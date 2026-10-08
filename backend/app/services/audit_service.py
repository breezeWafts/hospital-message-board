"""审计日志服务：全流程日志，只追加不修改，永久保留。

日志字段固定：操作人、角色、IP、UA、时间、动作、前状态、后状态、留言 ID、任务 ID。
"""
from app.db import database as db

INSERT_SQL = """
    INSERT INTO audit_logs(operator_id, operator_name, role, ip, ua, action,
                           before_status, after_status, message_id, task_id)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""


def log(
    conn,
    *,
    operator: dict | None = None,
    role: str | None = None,
    ip: str | None = None,
    ua: str | None = None,
    action: str,
    before_status: str | None = None,
    after_status: str | None = None,
    message_id: int | None = None,
    task_id: int | None = None,
) -> None:
    """写入一条审计日志。

    operator: 当前用户 dict（含 id/username/display_name/role），匿名/系统动作为 None。
    """
    operator_id = operator.get("id") if operator else None
    operator_name = None
    if operator:
        operator_name = operator.get("display_name") or operator.get("username")
    op_role = role if role is not None else (operator.get("role") if operator else None)
    db.execute(
        INSERT_SQL,
        (operator_id, operator_name, op_role, ip, ua, action,
         before_status, after_status, message_id, task_id),
        conn,
    )


# 日志查询：排序方向白名单，禁止拼接用户原始输入
_SORT_WHITELIST = {
    "created_at_desc": "created_at DESC",
    "created_at_asc": "created_at ASC",
    "id_desc": "id DESC",
    "id_asc": "id ASC",
}


def query_logs(
    *,
    action: str | None = None,
    operator: str | None = None,
    role: str | None = None,
    message_id: int | None = None,
    task_id: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    sort: str = "created_at_desc",
    page: int | None = None,
    page_size: int | None = None,
):
    """分页查询日志。operator 使用 LIKE（转义 \\、%、_）。"""
    p, s, offset, limit = db.page(page, page_size, max_size=100)
    where = []
    params: list = []
    if action:
        where.append("action = %s")
        params.append(action)
    if operator:
        where.append("operator_name LIKE %s ESCAPE '\\\\'")
        params.append(f"%{db.escape_like(operator)}%")
    if role:
        where.append("role = %s")
        params.append(role)
    if message_id is not None:
        where.append("message_id = %s")
        params.append(message_id)
    if task_id is not None:
        where.append("task_id = %s")
        params.append(task_id)
    if date_from:
        where.append("created_at >= %s::timestamptz")
        params.append(date_from)
    if date_to:
        where.append("created_at <= %s::timestamptz")
        params.append(date_to)
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    order_sql = db.whitelist_sort(sort, _SORT_WHITELIST, "created_at DESC")
    total = db.count(f"SELECT count(*) AS c FROM audit_logs {where_sql}", params)
    items = db.all(
        f"""SELECT id, operator_id, operator_name, role, ip, ua, action,
                   before_status, after_status, message_id, task_id, created_at
            FROM audit_logs {where_sql} ORDER BY {order_sql}
            LIMIT %s OFFSET %s""",
        params + [limit, offset],
    )
    return {"total": total, "page": p, "page_size": s, "items": items}
