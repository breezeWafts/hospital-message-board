"""任务服务：部门处理提交、秘书审核任务、任务查询（部门/秘书/院长）。

任务状态机：
    PENDING → REVIEWING → APPROVED（终态）
              ↓
           REJECTED → 回到 PENDING（保留 last_review_result / last_review_comment 与历史记录）
"""
from fastapi import HTTPException

from app.constants import AuditAction, MessageStatus, Role, TaskReview, TaskStatus
from app.db import database as db
from app.services import attachment_service, audit_service, message_service, notification_service


def get_task(task_id: int, viewer: dict, conn=None) -> dict:
    row = db.one(
        """SELECT t.*, d.name AS department_name, u.display_name AS assigner_name,
                  m.title AS message_title, m.status AS message_status
           FROM tasks t
           JOIN departments d ON d.id = t.department_id
           LEFT JOIN users u ON u.id = t.assigner_id
           JOIN messages m ON m.id = t.message_id
           WHERE t.id = %s""",
        (task_id,), conn,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    role = viewer["role"]
    if role == Role.DEPARTMENT and row["department_id"] != viewer.get("department_id"):
        raise HTTPException(status_code=403, detail="仅可查看本部门任务")
    return {
        "id": row["id"], "message_id": row["message_id"], "message_title": row["message_title"],
        "message_status": row["message_status"], "department_id": row["department_id"],
        "department_name": row["department_name"], "assigner_name": row["assigner_name"] or "—",
        "title": row["title"], "content": row["content"], "processing_content": row["processing_content"],
        "status": row["status"], "last_review_result": row["last_review_result"],
        "last_review_comment": row["last_review_comment"],
        "submitted_at": message_service._fmt(row["submitted_at"]),
        "approved_at": message_service._fmt(row["approved_at"]),
        "created_at": message_service._fmt(row["created_at"]),
        "updated_at": message_service._fmt(row["updated_at"]),
        "attachments": message_service._task_attachments(task_id, conn),
        "reviews": message_service._task_reviews(task_id, conn),
    }


_SORT_WHITELIST = {
    "created_at_desc": "created_at DESC",
    "created_at_asc": "created_at ASC",
    "id_desc": "id DESC",
    "id_asc": "id ASC",
    "updated_at_desc": "updated_at DESC",
    "updated_at_asc": "updated_at ASC",
}


def list_tasks(viewer: dict, *, status: str | None = None, message_id: int | None = None,
               page=None, page_size=None, sort: str = "created_at_desc") -> dict:
    role = viewer["role"]
    p, s, offset, limit = db.page(page, page_size)
    where, params = [], []
    if role == Role.DEPARTMENT:
        where.append("t.department_id = %s")
        params.append(viewer.get("department_id"))
    elif role not in (Role.SECRETARY, Role.ADMIN, Role.PRINCIPAL):
        raise HTTPException(status_code=403, detail="无权查看任务列表")
    if status:
        if status not in TaskStatus.ALL:
            raise HTTPException(status_code=400, detail=f"非法任务状态: {status}")
        where.append("t.status = %s")
        params.append(status)
    if message_id is not None:
        where.append("t.message_id = %s")
        params.append(message_id)
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    order_sql = db.whitelist_sort(sort, _SORT_WHITELIST, "created_at DESC")
    total = db.count(f"SELECT count(*) AS c FROM tasks t {where_sql}", params)
    rows = db.all(
        f"""SELECT t.id, t.message_id, m.title AS message_title, m.status AS message_status,
                   t.department_id, d.name AS department_name, t.title, t.content,
                   t.processing_content, t.status, t.last_review_result, t.submitted_at,
                   t.approved_at, t.created_at, t.updated_at
            FROM tasks t
            JOIN messages m ON m.id = t.message_id
            JOIN departments d ON d.id = t.department_id
            {where_sql} ORDER BY {order_sql} LIMIT %s OFFSET %s""",
        params + [limit, offset],
    )
    items = [
        {
            "id": r["id"], "message_id": r["message_id"], "message_title": r["message_title"],
            "message_status": r["message_status"], "department_id": r["department_id"],
            "department_name": r["department_name"], "title": r["title"], "content": r["content"],
            "processing_content": r["processing_content"], "status": r["status"],
            "last_review_result": r["last_review_result"],
            "submitted_at": message_service._fmt(r["submitted_at"]),
            "approved_at": message_service._fmt(r["approved_at"]),
            "created_at": message_service._fmt(r["created_at"]),
            "updated_at": message_service._fmt(r["updated_at"]),
        }
        for r in rows
    ]
    return {"total": total, "page": p, "page_size": s, "items": items}


def department_submit(user: dict, task_id: int, content: str, files: list[dict], ip: str, ua: str) -> dict:
    """部门负责人提交处理：上传附件、填写处理内容、提交。任务状态 → REVIEWING。"""
    content = (content or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="请填写处理内容")
    with db.tx() as conn:
        task = db.one("SELECT * FROM tasks WHERE id = %s", (task_id,), conn)
        if task is None:
            raise HTTPException(status_code=404, detail="任务不存在")
        if task["department_id"] != user.get("department_id"):
            raise HTTPException(status_code=403, detail="仅可处理本部门任务")
        # 全局锁序：message → task（与 message_service 一致，避免死锁环）
        message_service._get_message_locked(task["message_id"], conn)
        task = db.one("SELECT * FROM tasks WHERE id = %s FOR UPDATE", (task_id,), conn)
        if task["status"] != TaskStatus.PENDING:
            raise HTTPException(status_code=400, detail="任务不在待处理状态")
        stored_paths: list[str] = []
        try:
            for i, f in enumerate(files):
                attachment_service.validate_file(f["filename"], f["size"], i)
                data = f["data"]
                ext = attachment_service._ext_of(f["filename"])
                rel_path = attachment_service.store_bytes(data, ext)
                stored_paths.append(rel_path)
                db.execute(
                    """INSERT INTO task_attachments(task_id, original_name, stored_path, mime_type, size_bytes, sha256, uploaded_by)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (task_id, f["filename"], rel_path, f.get("mime"), f["size"],
                     attachment_service.sha256_of(data), user["id"]), conn,
                )
        except Exception:
            # 事务回滚时清理已落盘的孤儿附件
            attachment_service.remove_stored(stored_paths)
            raise
        db.execute(
            "UPDATE tasks SET processing_content = %s, status = %s, submitted_at = now(), updated_at = now() WHERE id = %s",
            (content, TaskStatus.REVIEWING, task_id), conn,
        )
        message_service._recompute_status(conn, task["message_id"])
        audit_service.log(
            conn, operator=user, ip=ip, ua=ua, action=AuditAction.TASK_SUBMIT,
            before_status=TaskStatus.PENDING, after_status=TaskStatus.REVIEWING,
            message_id=task["message_id"], task_id=task_id,
        )
        notification_service.notify_role(
            conn, Role.SECRETARY, subject="部门已提交处理",
            content=f"留言 #{task['message_id']} 任务 #{task_id}「{task['title']}」已提交，请审核。",
            related_type="task", related_id=task_id,
        )
        return get_task(task_id, {"role": user["role"], "department_id": user.get("department_id")}, conn)


def task_review(user: dict, task_id: int, result: str, comment: str | None, ip: str, ua: str) -> dict:
    """秘书审核部门任务：通过 / 驳回（驳回必须填写批注，任务回到 PENDING，留言回到 PENDING）。"""
    if result not in (TaskReview.APPROVED, TaskReview.REJECTED):
        raise HTTPException(status_code=400, detail="非法审核结果")
    with db.tx() as conn:
        task = db.one("SELECT * FROM tasks WHERE id = %s", (task_id,), conn)
        if task is None:
            raise HTTPException(status_code=404, detail="任务不存在")
        msg_id = task["message_id"]
        # 全局锁序：message → task（与 message_service 一致，避免死锁环）
        message_service._get_message_locked(msg_id, conn)
        task = db.one("SELECT * FROM tasks WHERE id = %s FOR UPDATE", (task_id,), conn)
        if task["status"] != TaskStatus.REVIEWING:
            raise HTTPException(status_code=400, detail="任务不在待审核状态")
        if result == TaskReview.REJECTED and not (comment or "").strip():
            raise HTTPException(status_code=400, detail="驳回必须填写批注")
        if result == TaskReview.APPROVED:
            db.execute(
                """UPDATE tasks SET status = %s, approved_at = now(), last_review_result = %s,
                       last_review_comment = %s, updated_at = now() WHERE id = %s""",
                (TaskStatus.APPROVED, TaskReview.APPROVED, (comment or "").strip() or None, task_id), conn,
            )
        else:
            db.execute(
                """UPDATE tasks SET status = %s, last_review_result = %s, last_review_comment = %s,
                       updated_at = now() WHERE id = %s""",
                (TaskStatus.PENDING, TaskReview.REJECTED, comment.strip(), task_id), conn,
            )
        db.execute(
            "INSERT INTO reviews(message_id, task_id, reviewer_id, result, comment) VALUES (%s, %s, %s, %s, %s)",
            (msg_id, task_id, user["id"], result, (comment or "").strip() or None), conn,
        )
        message_service._recompute_status(conn, msg_id)
        audit_service.log(
            conn, operator=user, ip=ip, ua=ua, action=AuditAction.TASK_REVIEW,
            before_status=TaskStatus.REVIEWING,
            after_status=TaskStatus.APPROVED if result == TaskReview.APPROVED else TaskStatus.PENDING,
            message_id=msg_id, task_id=task_id,
        )
        if result == TaskReview.APPROVED:
            if message_service._all_tasks_approved(conn, msg_id):
                # 全部任务通过 → 通知院长最终确认（留言保持 REVIEWING）
                db.execute(
                    "UPDATE messages SET status = %s, updated_at = now() WHERE id = %s",
                    (MessageStatus.REVIEWING, msg_id), conn,
                )
                notification_service.notify_role(
                    conn, Role.PRINCIPAL, subject="留言待最终确认",
                    content=f"留言 #{msg_id} 全部任务已通过秘书审核，请您最终确认。",
                    related_type="message", related_id=msg_id,
                )
        else:
            notification_service.notify_department(
                conn, task["department_id"], subject="任务被驳回",
                content=f"留言 #{msg_id} 任务 #{task_id}「{task['title']}」被驳回：{comment}，请重新处理。",
                related_type="task", related_id=task_id,
            )
        return get_task(task_id, {"role": user["role"], "department_id": user.get("department_id")}, conn)
