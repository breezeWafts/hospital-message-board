"""留言服务：匿名提交/查询/评价、秘书审核、院长批示/确认/驳回、任务分派、归档。

状态机（v2.2）：
    NEW ──秘书审核通过──> NEW(secretary_review_result=APPROVED，待院长批示) ──院长批示──> PENDING
     │
     └──秘书驳回/拒绝──> REJECTED ──归档──> ARCHIVED
    PENDING ──部门提交──> REVIEWING
    REVIEWING ──全部任务通过且院长确认──> COMPLETED
    REVIEWING ──院长/秘书驳回──> PENDING
    COMPLETED ──匿名评价满意/秘书归档──> ARCHIVED
    COMPLETED ──匿名评价不满意──> COMPLETED(evaluation_satisfied=false)

聚合规则：ARCHIVED / REJECTED 不再被任务状态聚合重算覆盖。
任务相关函数见 task_service.py。
"""
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException

from app.constants import (
    AuditAction,
    MessageStatus,
    Role,
    SecretaryReview,
    TaskStatus,
)
from app.core import security
from app.db import database as db
from app.services import (
    attachment_service,
    audit_service,
    config_service,
    notification_service,
)

MESSAGE_BASE_COLS = (
    "id, title, content, status, captcha_attempts, captcha_locked_until, captcha_expires_at, "
    "submit_ip, submit_ua, evaluation_satisfied, principal_instruction, "
    "secretary_review_result, secretary_reviewer_id, secretary_reviewed_at, "
    "secretary_review_comment, completed_at, archived_at, created_at, updated_at"
)

# ---------------- 基础助手 ----------------

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _get_message(msg_id: int, conn=None) -> dict | None:
    return db.one(f"SELECT {MESSAGE_BASE_COLS} FROM messages WHERE id = %s", (msg_id,), conn)


def _get_message_locked(msg_id: int, conn) -> dict | None:
    """读取并锁定留言行（写路径用，串行化并发操作，防止重复审核/评价）。"""
    return db.one(f"SELECT {MESSAGE_BASE_COLS} FROM messages WHERE id = %s FOR UPDATE", (msg_id,), conn)


def _check_visible_basic(status: str):
    if status not in MessageStatus.ALL:
        raise HTTPException(status_code=400, detail=f"非法状态: {status}")


def _recompute_status(conn, message_id: int) -> str:
    """留言状态由任务状态聚合计算；ARCHIVED / REJECTED 不再被重算覆盖。"""
    msg = db.one("SELECT status FROM messages WHERE id = %s FOR UPDATE", (message_id,), conn)
    if msg is None:
        return MessageStatus.NEW
    if msg["status"] in (MessageStatus.ARCHIVED, MessageStatus.REJECTED):
        return msg["status"]
    rows = db.all("SELECT status FROM tasks WHERE message_id = %s", (message_id,), conn)
    if not rows:
        return msg["status"]
    statuses = {r["status"] for r in rows}
    new_status = msg["status"]
    if TaskStatus.PENDING in statuses:
        new_status = MessageStatus.PENDING
    elif TaskStatus.REVIEWING in statuses:
        new_status = MessageStatus.REVIEWING
    elif statuses == {TaskStatus.APPROVED}:
        # 全部任务通过但院长未确认 → 保持 REVIEWING（待院长最终确认）
        new_status = MessageStatus.REVIEWING
    if new_status != msg["status"]:
        db.execute(
            "UPDATE messages SET status = %s, updated_at = now() WHERE id = %s",
            (new_status, message_id), conn,
        )
    return new_status


def _all_tasks_approved(conn, message_id: int) -> bool:
    pending = db.scalar(
        "SELECT count(*) AS c FROM tasks WHERE message_id = %s AND status <> %s",
        (message_id, TaskStatus.APPROVED), conn,
    )
    total = db.scalar("SELECT count(*) AS c FROM tasks WHERE message_id = %s", (message_id,), conn)
    return total > 0 and int(pending) == 0


# ---------------- 匿名：提交 ----------------

def create_message(conn, *, title: str, content: str, files: list[dict], ip: str, ua: str):
    """匿名提交留言。返回 (留言编号, 查询验证码)。留言编号即 messages.id。"""
    title = (title or "").strip()
    content = (content or "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="标题不能为空")
    if not content:
        raise HTTPException(status_code=400, detail="内容不能为空")
    if len(title) > 200 or len(content) > 20000:
        raise HTTPException(status_code=400, detail="标题或内容过长")

    ttl_days = config_service.get_int("captcha_ttl_days", 30)
    captcha = security.generate_captcha()
    msg_id = db.scalar(
        """INSERT INTO messages(title, content, status, captcha_hash, captcha_expires_at, submit_ip, submit_ua)
           VALUES (%s, %s, %s, %s, now() + (%s || ' days')::interval, %s, %s) RETURNING id""",
        (title, content, MessageStatus.NEW, security.hash_captcha(captcha), ttl_days, ip, ua),
        conn,
    )

    stored_paths: list[str] = []
    try:
        for i, f in enumerate(files):
            attachment_service.validate_file(f["filename"], f["size"], i)
            data = f["data"]
            ext = attachment_service._ext_of(f["filename"])
            rel_path = attachment_service.store_bytes(data, ext)
            stored_paths.append(rel_path)
            db.execute(
                """INSERT INTO message_attachments(message_id, original_name, stored_path, mime_type, size_bytes, sha256)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (msg_id, f["filename"], rel_path, f.get("mime"), f["size"],
                 attachment_service.sha256_of(data)),
                conn,
            )
    except Exception:
        # 事务回滚时清理已落盘的孤儿附件
        attachment_service.remove_stored(stored_paths)
        raise

    audit_service.log(
        conn, role=Role.ANONYMOUS, operator_name=f"匿名(IP:{ip})", ip=ip, ua=ua,
        action=AuditAction.ANON_SUBMIT, before_status=None, after_status=MessageStatus.NEW,
        message_id=msg_id,
    )
    notification_service.notify_role(
        conn, Role.SECRETARY, subject="新匿名留言待审核",
        content=f"留言 #{msg_id}《{title}》已提交，请及时审核。", related_type="message", related_id=msg_id,
    )
    return msg_id, captcha


# ---------------- 匿名：查询验证码校验 ----------------

def _captcha_hash_of(conn, msg_id: int) -> str:
    return db.scalar("SELECT captcha_hash FROM messages WHERE id = %s", (msg_id,), conn)


def _check_captcha(conn, msg: dict, captcha: str, ip: str, ua: str):
    """校验查询验证码，返回 (ok, error_code, locked_until_iso, attempts_left)。

    失败路径的 attempts 计数/锁定写在当前连接内，由调用方在事务提交后抛出异常，
    保证"错误 5 次锁定"的计数不会被回滚丢弃。
    """
    max_attempts = config_service.get_int("captcha_max_attempts", 5)
    lock_days = config_service.get_int("captcha_lock_days", 30)
    locked_until = msg.get("captcha_locked_until")
    if locked_until and locked_until > _now():
        return False, "LOCKED", locked_until.isoformat(), 0
    if msg["captcha_expires_at"] < _now():
        return False, "EXPIRED", None, 0
    if not security.verify_captcha(captcha, _captcha_hash_of(conn, msg["id"])):
        attempts = (msg.get("captcha_attempts") or 0) + 1
        locked = None
        if attempts >= max_attempts:
            locked = _now() + timedelta(days=lock_days)
        db.execute(
            "UPDATE messages SET captcha_attempts = %s, captcha_locked_until = %s, updated_at = now() WHERE id = %s",
            (attempts, locked, msg["id"]), conn,
        )
        audit_service.log(
            conn, role=Role.ANONYMOUS, operator_name=f"匿名(IP:{ip})", ip=ip, ua=ua,
            action=AuditAction.ANON_QUERY_FAILED, message_id=msg["id"],
        )
        return False, "WRONG", locked.isoformat() if locked else None, max(0, max_attempts - attempts)
    db.execute(
        "UPDATE messages SET captcha_attempts = 0, updated_at = now() WHERE id = %s", (msg["id"],), conn
    )
    audit_service.log(
        conn, role=Role.ANONYMOUS, operator_name=f"匿名(IP:{ip})", ip=ip, ua=ua,
        action=AuditAction.ANON_QUERY, message_id=msg["id"],
    )
    return True, None, None, 0


def _raise_captcha_error(err: str, locked_until: str | None, attempts_left: int) -> None:
    if err == "LOCKED":
        raise HTTPException(
            status_code=423,
            detail={"message": "验证码已锁定，请联系管理员重置", "locked_until": locked_until},
        )
    if err == "EXPIRED":
        raise HTTPException(status_code=400, detail="查询验证码已过期，请联系管理员")
    raise HTTPException(
        status_code=400,
        detail={"message": "验证码错误", "attempts_left": attempts_left},
    )


# ---------------- 序列化 ----------------

def _fmt(dt) -> str | None:
    return dt.isoformat() if isinstance(dt, datetime) else dt


def _message_attachments(msg_id: int, conn=None) -> list[dict]:
    rows = db.all(
        "SELECT id, original_name, size_bytes, mime_type, created_at FROM message_attachments "
        "WHERE message_id = %s ORDER BY id",
        (msg_id,), conn,
    )
    return [
        {
            "id": r["id"], "original_name": r["original_name"], "size_bytes": r["size_bytes"],
            "mime_type": r["mime_type"], "created_at": _fmt(r["created_at"]),
            "download_url": f"/api/attachments/message/{r['id']}",
        }
        for r in rows
    ]


def _task_attachments(task_id: int, conn=None) -> list[dict]:
    rows = db.all(
        "SELECT id, original_name, size_bytes, mime_type, created_at FROM task_attachments "
        "WHERE task_id = %s ORDER BY id",
        (task_id,), conn,
    )
    return [
        {
            "id": r["id"], "original_name": r["original_name"], "size_bytes": r["size_bytes"],
            "mime_type": r["mime_type"], "created_at": _fmt(r["created_at"]),
            "download_url": f"/api/attachments/task/{r['id']}",
        }
        for r in rows
    ]


def _task_reviews(task_id: int, conn=None) -> list[dict]:
    rows = db.all(
        """SELECT r.result, r.comment, r.created_at, u.display_name AS reviewer_name, u.username, u.role
           FROM reviews r JOIN users u ON u.id = r.reviewer_id
           WHERE r.task_id = %s ORDER BY r.id""",
        (task_id,), conn,
    )
    return [
        {
            "result": r["result"], "comment": r["comment"], "created_at": _fmt(r["created_at"]),
            "reviewer_name": r["reviewer_name"] or r["username"], "role": r["role"],
        }
        for r in rows
    ]


def _message_reviews(msg_id: int, conn=None) -> list[dict]:
    rows = db.all(
        """SELECT r.id, r.result, r.comment, r.created_at, r.task_id,
                  u.display_name AS reviewer_name, u.username, u.role
           FROM reviews r JOIN users u ON u.id = r.reviewer_id
           WHERE r.message_id = %s AND r.task_id IS NULL ORDER BY r.id""",
        (msg_id,), conn,
    )
    return [
        {
            "id": r["id"], "result": r["result"], "comment": r["comment"],
            "created_at": _fmt(r["created_at"]),
            "reviewer_name": r["reviewer_name"] or r["username"], "role": r["role"],
        }
        for r in rows
    ]


def _workflow(msg: dict, tasks: list[dict], conn=None) -> dict:
    """工作流节点/时间线（供前端 Vue Flow 渲染）。"""
    loops = []
    for t in tasks:
        for r in t.get("reviews", []):
            if r["result"] in ("REJECTED", "REFUSED"):
                loops.append({
                    "task_id": t["id"], "department": t.get("department_name"),
                    "at": r["created_at"], "comment": r["comment"],
                })
    status = msg["status"]
    reached_map = {
        "SUBMITTED": True,
        "SECRETARY_REVIEW": msg.get("secretary_review_result") is not None,
        "PRINCIPAL_INSTRUCTION": bool(msg.get("principal_instruction"))
        or status not in (MessageStatus.NEW,),
        "DEPARTMENT_PROCESSING": bool(tasks),
        "SECRETARY_TASK_REVIEW": any(
            t["status"] in (TaskStatus.REVIEWING, TaskStatus.APPROVED) for t in tasks
        ),
        "PRINCIPAL_CONFIRM": status in (MessageStatus.COMPLETED, MessageStatus.ARCHIVED),
        "EVALUATION": msg.get("evaluation_satisfied") is not None,
        "ARCHIVED": bool(msg.get("archived_at")),
    }
    task_created_times = [t.get("created_at") or "" for t in tasks]
    at_map = {
        "SUBMITTED": msg.get("created_at"),
        "SECRETARY_REVIEW": msg.get("secretary_reviewed_at"),
        "PRINCIPAL_INSTRUCTION": None,
        "DEPARTMENT_PROCESSING": min(task_created_times, default="") if task_created_times else None,
        "SECRETARY_TASK_REVIEW": None,
        "PRINCIPAL_CONFIRM": msg.get("completed_at"),
        "EVALUATION": None,
        "ARCHIVED": msg.get("archived_at"),
    }
    labels = {
        "SUBMITTED": "匿名提交", "SECRETARY_REVIEW": "秘书审核",
        "PRINCIPAL_INSTRUCTION": "院长批示", "DEPARTMENT_PROCESSING": "部门处理",
        "SECRETARY_TASK_REVIEW": "秘书复核", "PRINCIPAL_CONFIRM": "院长确认",
        "EVALUATION": "匿名评价", "ARCHIVED": "归档",
    }
    current = status
    if status == MessageStatus.NEW:
        current = "SECRETARY_REVIEW" if msg.get("secretary_review_result") else "SUBMITTED"
    elif status == MessageStatus.REJECTED:
        current = "SECRETARY_REVIEW"
    stages = [
        {"key": k, "label": v, "reached": reached_map.get(k, False), "at": _fmt(at_map.get(k))}
        for k, v in labels.items()
    ]
    return {"current": current, "stages": stages, "loops": loops}


def _serialize_message(msg: dict) -> dict:
    if not msg:
        return {}
    return {
        "id": msg["id"], "title": msg["title"], "content": msg["content"], "status": msg["status"],
        "created_at": _fmt(msg["created_at"]), "updated_at": _fmt(msg["updated_at"]),
        "completed_at": _fmt(msg.get("completed_at")), "archived_at": _fmt(msg.get("archived_at")),
        "evaluation_satisfied": msg.get("evaluation_satisfied"),
        "principal_instruction": msg.get("principal_instruction"),
        "secretary_review_result": msg.get("secretary_review_result"),
        "secretary_review_comment": msg.get("secretary_review_comment"),
        "secretary_reviewed_at": _fmt(msg.get("secretary_reviewed_at")),
        "captcha_expires_at": _fmt(msg.get("captcha_expires_at")),
    }


# ---------------- 匿名：查询 / 评价 ----------------

def query_anonymous(msg_id: int, captcha: str, ip: str, ua: str) -> dict:
    # 第一步：验证码校验（独立事务；失败计数/锁定必须落库后再抛错）
    with db.tx() as conn:
        msg = _get_message(msg_id, conn)
        if msg is None:
            raise HTTPException(status_code=404, detail="留言不存在")
        ok, err, locked_until, attempts_left = _check_captcha(conn, msg, captcha, ip, ua)
    if not ok:
        _raise_captcha_error(err, locked_until, attempts_left)
    # 第二步：只读返回详情
    with db.tx() as conn:
        msg = _get_message(msg_id, conn)
        if msg["status"] not in MessageStatus.ANON_VIEWABLE:
            # 未完成/未归档：只回显基本状态，不暴露部门附件与驳回批注
            return {
                "id": msg["id"], "title": msg["title"], "status": msg["status"],
                "created_at": _fmt(msg["created_at"]), "updated_at": _fmt(msg["updated_at"]),
                "captcha_expires_at": _fmt(msg["captcha_expires_at"]),
            }
        tasks = _tasks_with_visibility(msg_id, viewer_role=Role.ANONYMOUS, conn=conn)
        base = _serialize_message(msg)
        base.update({
            "can_evaluate": msg["status"] == MessageStatus.COMPLETED
            and msg.get("evaluation_satisfied") is None,
            "attachments": _with_anon_tokens(_message_attachments(msg_id, conn), msg_id),
            "tasks": _attach_tokens_to_tasks(tasks, msg_id),
            "reviews": _message_reviews(msg_id, conn),
            "workflow": _workflow(msg, tasks, conn),
        })
        return base


def _with_anon_tokens(attachments: list[dict], msg_id: int) -> list[dict]:
    """为匿名用户附件下载 URL 附加短时效签名令牌（附件下载走后端鉴权）。"""
    out = []
    for a in attachments:
        item = dict(a)
        item["download_url"] = f"{a['download_url']}?anon_token={security.sign_anon_token(a['id'], msg_id)}"
        out.append(item)
    return out


def _attach_tokens_to_tasks(tasks: list[dict], msg_id: int) -> list[dict]:
    for t in tasks:
        t["attachments"] = _with_anon_tokens(t.get("attachments") or [], msg_id)
    return tasks


def evaluate(msg_id: int, captcha: str, satisfied: bool, content: str | None, ip: str, ua: str) -> dict:
    # 第一步：验证码校验（失败计数/锁定落库后抛错）
    with db.tx() as conn:
        msg = _get_message_locked(msg_id, conn)
        if msg is None:
            raise HTTPException(status_code=404, detail="留言不存在")
        ok, err, locked_until, attempts_left = _check_captcha(conn, msg, captcha, ip, ua)
    if not ok:
        _raise_captcha_error(err, locked_until, attempts_left)
    # 第二步：评价写入
    with db.tx() as conn:
        msg = _get_message_locked(msg_id, conn)
        if msg["status"] != MessageStatus.COMPLETED:
            raise HTTPException(status_code=400, detail="留言尚未完成，暂不能评价")
        if msg.get("evaluation_satisfied") is not None:
            raise HTTPException(status_code=400, detail="该留言已评价")
        db.execute(
            "INSERT INTO evaluations(message_id, satisfied, content) VALUES (%s, %s, %s)",
            (msg_id, satisfied, (content or "").strip() or None), conn,
        )
        after = MessageStatus.COMPLETED
        if satisfied:
            after = MessageStatus.ARCHIVED
            db.execute(
                "UPDATE messages SET evaluation_satisfied = TRUE, status = %s, archived_at = now(), "
                "updated_at = now() WHERE id = %s",
                (after, msg_id), conn,
            )
        else:
            db.execute(
                "UPDATE messages SET evaluation_satisfied = FALSE, updated_at = now() WHERE id = %s",
                (msg_id,), conn,
            )
        audit_service.log(
            conn, role=Role.ANONYMOUS, operator_name=f"匿名(IP:{ip})", ip=ip, ua=ua,
            action=AuditAction.ANON_EVALUATE, before_status=MessageStatus.COMPLETED,
            after_status=after, message_id=msg_id,
        )
        notification_service.notify_role(
            conn, Role.SECRETARY, subject="匿名用户已评价",
            content=f"留言 #{msg_id} 收到评价：{'满意' if satisfied else '不满意'}。",
            related_type="message", related_id=msg_id,
        )
        if not satisfied:
            # 秘书再通知院长（当前 mock）
            notification_service.notify_role(
                conn, Role.PRINCIPAL, subject="匿名评价不满意",
                content=f"留言 #{msg_id} 匿名评价为不满意，请关注后续处理。",
                related_type="message", related_id=msg_id,
            )
        updated = _get_message(msg_id, conn)
        return _serialize_message(updated)


# ---------------- 秘书：审核留言 / 分派 / 归档 ----------------

def secretary_review(user: dict, msg_id: int, result: str, comment: str | None,
                     ip: str, ua: str) -> dict:
    if result not in SecretaryReview.ALL:
        raise HTTPException(status_code=400, detail="非法审核结果")
    with db.tx() as conn:
        msg = _get_message_locked(msg_id, conn)
        if msg is None:
            raise HTTPException(status_code=404, detail="留言不存在")
        if msg["status"] != MessageStatus.NEW:
            raise HTTPException(status_code=400, detail="仅待审核留言可执行审核")
        if msg.get("secretary_review_result") is not None:
            raise HTTPException(status_code=400, detail="该留言已审核")
        if result in (SecretaryReview.REJECTED, SecretaryReview.REFUSED) and not (comment or "").strip():
            raise HTTPException(status_code=400, detail="驳回/拒绝必须填写原因")
        before = msg["status"]
        after = before
        if result == SecretaryReview.APPROVED:
            db.execute(
                """UPDATE messages SET secretary_review_result = %s, secretary_reviewer_id = %s,
                       secretary_reviewed_at = now(), secretary_review_comment = %s, updated_at = now()
                   WHERE id = %s""",
                (result, user["id"], (comment or "").strip() or None, msg_id), conn,
            )
            # 留言仍为 NEW，进入“待院长批示”视图
        else:
            db.execute(
                """UPDATE messages SET secretary_review_result = %s, secretary_reviewer_id = %s,
                       secretary_reviewed_at = now(), secretary_review_comment = %s,
                       status = %s, updated_at = now()
                   WHERE id = %s""",
                (result, user["id"], (comment or "").strip(), MessageStatus.REJECTED, msg_id), conn,
            )
            after = MessageStatus.REJECTED
        db.execute(
            "INSERT INTO reviews(message_id, task_id, reviewer_id, result, comment) VALUES (%s, NULL, %s, %s, %s)",
            (msg_id, user["id"], result, (comment or "").strip() or None), conn,
        )
        audit_service.log(
            conn, operator=user, ip=ip, ua=ua, action=AuditAction.SECRETARY_REVIEW,
            before_status=before, after_status=after, message_id=msg_id,
        )
        if result == SecretaryReview.APPROVED:
            notification_service.notify_role(
                conn, Role.PRINCIPAL, subject="留言待院长批示",
                content=f"留言 #{msg_id}《{msg['title']}》已通过秘书审核，请您批示。",
                related_type="message", related_id=msg_id,
            )
        # 驳回/拒绝：不通知匿名用户，仅记录审计日志
        return _serialize_message(_get_message(msg_id, conn))


def principal_instruction(user: dict, msg_id: int, instruction: str, ip: str, ua: str) -> dict:
    with db.tx() as conn:
        msg = _get_message_locked(msg_id, conn)
        if msg is None:
            raise HTTPException(status_code=404, detail="留言不存在")
        if msg["status"] != MessageStatus.NEW or msg.get("secretary_review_result") != SecretaryReview.APPROVED:
            raise HTTPException(status_code=400, detail="该留言不在待批示状态")
        db.execute(
            "UPDATE messages SET principal_instruction = %s, status = %s, updated_at = now() WHERE id = %s",
            (instruction.strip(), MessageStatus.PENDING, msg_id), conn,
        )
        audit_service.log(
            conn, operator=user, ip=ip, ua=ua, action=AuditAction.PRINCIPAL_INSTRUCTION,
            before_status=MessageStatus.NEW, after_status=MessageStatus.PENDING, message_id=msg_id,
        )
        notification_service.notify_role(
            conn, Role.SECRETARY, subject="院长已批示",
            content=f"留言 #{msg_id} 院长已批示，请将其分解为部门任务并分派。",
            related_type="message", related_id=msg_id,
        )
        return _serialize_message(_get_message(msg_id, conn))


def assign_tasks(user: dict, msg_id: int, tasks: list[dict], ip: str, ua: str) -> dict:
    """秘书将留言分解为一个或多个部门任务并分派（也用于驳回后的二次分派）。"""
    if not tasks:
        raise HTTPException(status_code=400, detail="至少需要分派一个任务")
    with db.tx() as conn:
        msg = _get_message(msg_id, conn)
        if msg is None:
            raise HTTPException(status_code=404, detail="留言不存在")
        if msg["status"] != MessageStatus.PENDING:
            raise HTTPException(status_code=400, detail="仅院长批示后（PENDING）可分派任务")
        created = []
        for t in tasks:
            dept = db.one("SELECT id, name, is_active FROM departments WHERE id = %s", (t["department_id"],), conn)
            if dept is None:
                raise HTTPException(status_code=400, detail=f"部门不存在: {t['department_id']}")
            if not dept["is_active"]:
                raise HTTPException(status_code=400, detail=f"部门已停用: {dept['name']}")
            if not (t.get("title") or "").strip():
                raise HTTPException(status_code=400, detail="任务标题不能为空")
            task_id = db.scalar(
                """INSERT INTO tasks(message_id, department_id, assigner_id, title, content, status)
                   VALUES (%s, %s, %s, %s, %s, %s) RETURNING id""",
                (msg_id, dept["id"], user["id"], t["title"].strip(),
                 (t.get("content") or "").strip() or None, TaskStatus.PENDING), conn,
            )
            created.append(task_id)
            audit_service.log(
                conn, operator=user, ip=ip, ua=ua, action=AuditAction.TASKS_ASSIGNED,
                before_status=None, after_status=TaskStatus.PENDING,
                message_id=msg_id, task_id=task_id,
            )
            notification_service.notify_department(
                conn, dept["id"], subject="新的部门任务",
                content=f"留言 #{msg_id} 已分派任务「{t['title']}」至{dept['name']}，请及时处理。",
                related_type="task", related_id=task_id,
            )
        _recompute_status(conn, msg_id)
        return {"id": msg_id, "status": _get_message(msg_id, conn)["status"],
                "task_ids": created, "task_count": len(created)}


def archive(user: dict, msg_id: int, ip: str, ua: str) -> dict:
    """秘书归档：评价结束、无需继续处理的留言（COMPLETED / REJECTED → ARCHIVED）。"""
    with db.tx() as conn:
        msg = _get_message(msg_id, conn)
        if msg is None:
            raise HTTPException(status_code=404, detail="留言不存在")
        if msg["status"] not in (MessageStatus.COMPLETED, MessageStatus.REJECTED):
            raise HTTPException(status_code=400, detail="仅已完成或被驳回的留言可归档")
        db.execute(
            "UPDATE messages SET status = %s, archived_at = now(), updated_at = now() WHERE id = %s",
            (MessageStatus.ARCHIVED, msg_id), conn,
        )
        audit_service.log(
            conn, operator=user, ip=ip, ua=ua, action=AuditAction.ARCHIVE,
            before_status=msg["status"], after_status=MessageStatus.ARCHIVED, message_id=msg_id,
        )
        return _serialize_message(_get_message(msg_id, conn))


# ---------------- 院长：确认 / 驳回 ----------------

def principal_confirm(user: dict, msg_id: int, ip: str, ua: str) -> dict:
    with db.tx() as conn:
        msg = _get_message_locked(msg_id, conn)
        if msg is None:
            raise HTTPException(status_code=404, detail="留言不存在")
        if msg["status"] != MessageStatus.REVIEWING or not _all_tasks_approved(conn, msg_id):
            raise HTTPException(status_code=400, detail="留言不在待最终确认状态（需全部任务已通过）")
        db.execute(
            "UPDATE messages SET status = %s, completed_at = now(), updated_at = now() WHERE id = %s",
            (MessageStatus.COMPLETED, msg_id), conn,
        )
        audit_service.log(
            conn, operator=user, ip=ip, ua=ua, action=AuditAction.PRINCIPAL_CONFIRM,
            before_status=MessageStatus.REVIEWING, after_status=MessageStatus.COMPLETED, message_id=msg_id,
        )
        # 不通知匿名用户，匿名用户自行查询
        return _serialize_message(_get_message(msg_id, conn))


def principal_reject(user: dict, msg_id: int, comment: str, ip: str, ua: str) -> dict:
    """院长确认不通过：相关任务回到 PENDING，留言回到 PENDING，驳回到秘书。"""
    from app.constants import TaskReview  # 局部导入避免顶层循环

    with db.tx() as conn:
        # 全局锁序：message → task（与 task_service 一致，避免死锁环）
        msg = _get_message_locked(msg_id, conn)
        if msg is None:
            raise HTTPException(status_code=404, detail="留言不存在")
        if msg["status"] != MessageStatus.REVIEWING or not _all_tasks_approved(conn, msg_id):
            raise HTTPException(status_code=400, detail="留言不在待最终确认状态")
        approved_tasks = db.all(
            "SELECT id FROM tasks WHERE message_id = %s AND status = %s FOR UPDATE",
            (msg_id, TaskStatus.APPROVED), conn,
        )
        for t in approved_tasks:
            db.execute(
                """UPDATE tasks SET status = %s, last_review_result = %s, last_review_comment = %s,
                       updated_at = now() WHERE id = %s""",
                (TaskStatus.PENDING, TaskReview.REJECTED, comment.strip(), t["id"]), conn,
            )
            db.execute(
                "INSERT INTO reviews(message_id, task_id, reviewer_id, result, comment) VALUES (%s, %s, %s, %s, %s)",
                (msg_id, t["id"], user["id"], TaskReview.REJECTED, comment.strip()), conn,
            )
            audit_service.log(
                conn, operator=user, ip=ip, ua=ua, action=AuditAction.PRINCIPAL_REJECT,
                before_status=TaskStatus.APPROVED, after_status=TaskStatus.PENDING,
                message_id=msg_id, task_id=t["id"],
            )
        db.execute(
            "UPDATE messages SET status = %s, updated_at = now() WHERE id = %s",
            (MessageStatus.PENDING, msg_id), conn,
        )
        notification_service.notify_role(
            conn, Role.SECRETARY, subject="院长驳回最终确认",
            content=f"留言 #{msg_id} 院长确认不通过：{comment}，请驳回部门或重新分派。",
            related_type="message", related_id=msg_id,
        )
        return _serialize_message(_get_message(msg_id, conn))


# ---------------- 管理员：重置验证码锁定 ----------------

def reset_captcha_lock(user: dict, msg_id: int, ip: str, ua: str) -> dict:
    """仅解除锁定：captcha_attempts = 0, captcha_locked_until = NULL。

    不重新生成验证码，不修改 captcha_hash。
    """
    with db.tx() as conn:
        msg = _get_message(msg_id, conn)
        if msg is None:
            raise HTTPException(status_code=404, detail="留言不存在")
        db.execute(
            "UPDATE messages SET captcha_attempts = 0, captcha_locked_until = NULL, updated_at = now() WHERE id = %s",
            (msg_id,), conn,
        )
        audit_service.log(
            conn, operator=user, ip=ip, ua=ua, action=AuditAction.CAPTCHA_RESET, message_id=msg_id,
        )
    return {"ok": True, "message_id": msg_id}


# ---------------- 列表 / 详情（角色可见性）----------------

def _tasks_with_visibility(msg_id: int, viewer_role: str, department_id: int | None = None, conn=None) -> list[dict]:
    rows = db.all(
        """SELECT t.id, t.message_id, t.department_id, d.name AS department_name, t.assigner_id,
                  u.display_name AS assigner_name, t.title, t.content, t.processing_content, t.status,
                  t.last_review_result, t.last_review_comment, t.submitted_at, t.approved_at,
                  t.created_at, t.updated_at
           FROM tasks t
           JOIN departments d ON d.id = t.department_id
           LEFT JOIN users u ON u.id = t.assigner_id
           WHERE t.message_id = %s ORDER BY t.id""",
        (msg_id,), conn,
    )
    result = []
    for t in rows:
        if viewer_role == Role.DEPARTMENT and t["department_id"] != department_id:
            continue
        item = {
            "id": t["id"], "message_id": t["message_id"], "department_id": t["department_id"],
            "department_name": t["department_name"], "assigner_name": t["assigner_name"] or "—",
            "title": t["title"], "content": t["content"], "processing_content": t["processing_content"],
            "status": t["status"], "last_review_result": t["last_review_result"],
            "last_review_comment": t["last_review_comment"],
            "submitted_at": _fmt(t["submitted_at"]), "approved_at": _fmt(t["approved_at"]),
            "created_at": _fmt(t["created_at"]), "updated_at": _fmt(t["updated_at"]),
            "reviews": _task_reviews(t["id"], conn),
        }
        if viewer_role == Role.ANONYMOUS:
            # 匿名用户仅可见任务已通过（APPROVED）的附件
            if t["status"] == TaskStatus.APPROVED:
                item["attachments"] = _task_attachments(t["id"], conn)
            else:
                item["attachments"] = []
        else:
            item["attachments"] = _task_attachments(t["id"], conn)
        result.append(item)
    return result


def get_detail(msg_id: int, viewer: dict, conn=None) -> dict:
    """角色相关留言详情。viewer: 当前用户（含 role）。"""
    msg = _get_message(msg_id, conn)
    if msg is None:
        raise HTTPException(status_code=404, detail="留言不存在")
    role = viewer["role"]
    base = _serialize_message(msg)
    tasks = _tasks_with_visibility(msg_id, role, viewer.get("department_id"), conn)
    base["tasks"] = tasks
    base["reviews"] = _message_reviews(msg_id, conn)
    base["workflow"] = _workflow(msg, tasks, conn)
    base["can_evaluate"] = False
    reviewer = None
    if msg.get("secretary_reviewer_id"):
        reviewer = db.one(
            "SELECT display_name, username FROM users WHERE id = %s",
            (msg.get("secretary_reviewer_id"),), conn,
        )
    if role in (Role.SECRETARY, Role.ADMIN):
        base.update({
            "submit_ip": msg.get("submit_ip"), "submit_ua": msg.get("submit_ua"),
            "captcha_attempts": msg.get("captcha_attempts"),
            "captcha_locked_until": _fmt(msg.get("captcha_locked_until")),
            "attachments": _message_attachments(msg_id, conn),
            "evaluations": _evaluations(msg_id, conn),
            "secretary_reviewer_name": (reviewer["display_name"] or reviewer["username"]) if reviewer else None,
        })
    elif role == Role.PRINCIPAL:
        # 院长附件可见时点：匿名留言附件秘书审核通过后可见；任务附件该任务审核通过后可见
        if msg.get("secretary_review_result") == SecretaryReview.APPROVED:
            base["attachments"] = _message_attachments(msg_id, conn)
        else:
            base["attachments"] = []
        base["evaluations"] = _evaluations(msg_id, conn)
        base["secretary_reviewer_name"] = (reviewer["display_name"] or reviewer["username"]) if reviewer else None
    else:  # department 不应通过此入口查看整条留言
        base["attachments"] = []
    return base


def _evaluations(msg_id: int, conn=None) -> list[dict]:
    rows = db.all(
        "SELECT satisfied, content, created_at FROM evaluations WHERE message_id = %s ORDER BY id",
        (msg_id,), conn,
    )
    return [
        {"satisfied": r["satisfied"], "content": r["content"], "created_at": _fmt(r["created_at"])}
        for r in rows
    ]


_SORT_WHITELIST = {
    "created_at_desc": "created_at DESC",
    "created_at_asc": "created_at ASC",
    "id_desc": "id DESC",
    "id_asc": "id ASC",
    "updated_at_desc": "updated_at DESC",
    "updated_at_asc": "updated_at ASC",
}


def list_messages(viewer: dict, *, status: str | None = None, view: str = "all",
                  search: str | None = None, page=None, page_size=None, sort: str = "created_at_desc") -> dict:
    role = viewer["role"]
    p, s, offset, limit = db.page(page, page_size)
    where, params = [], []

    if role == Role.PRINCIPAL:
        if view == "instruction":
            # 院长批示视图：status = NEW AND secretary_review_result = APPROVED
            where.append("status = %s")
            params.append(MessageStatus.NEW)
            where.append("secretary_review_result = %s")
            params.append(SecretaryReview.APPROVED)
        elif view == "confirm":
            # 待最终确认：REVIEWING 且全部任务 APPROVED
            where.append("status = %s")
            params.append(MessageStatus.REVIEWING)
            where.append(
                "NOT EXISTS (SELECT 1 FROM tasks t WHERE t.message_id = m.id AND t.status <> %s)"
            )
            params.append(TaskStatus.APPROVED)
            where.append("EXISTS (SELECT 1 FROM tasks t WHERE t.message_id = m.id)")
        else:  # all：历史查看
            pass
    elif role in (Role.SECRETARY, Role.ADMIN):
        pass
    else:
        raise HTTPException(status_code=403, detail="无权查看留言列表")

    if status:
        _check_visible_basic(status)
        if not (role == Role.PRINCIPAL and view in ("instruction", "confirm")):
            where.append("m.status = %s")
            params.append(status)
    if search:
        where.append("(m.title LIKE %s ESCAPE '\\\\' OR m.content LIKE %s ESCAPE '\\\\')")
        like = f"%{db.escape_like(search)}%"
        params.extend([like, like])

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    order_sql = db.whitelist_sort(sort, _SORT_WHITELIST, "created_at DESC")
    total = db.count(f"SELECT count(*) AS c FROM messages m {where_sql}", params)
    rows = db.all(
        f"""SELECT m.*,
                   (SELECT count(*) FROM tasks t WHERE t.message_id = m.id) AS task_count,
                   (SELECT string_agg(d.name, '、' ORDER BY d.id)
                      FROM tasks t JOIN departments d ON d.id = t.department_id
                     WHERE t.message_id = m.id) AS department_names
            FROM messages m {where_sql}
            ORDER BY {order_sql} LIMIT %s OFFSET %s""",
        params + [limit, offset],
    )
    items = []
    for r in rows:
        item = _serialize_message(r)
        item["task_count"] = r["task_count"]
        item["department_names"] = r["department_names"]
        items.append(item)
    return {"total": total, "page": p, "page_size": s, "items": items}
