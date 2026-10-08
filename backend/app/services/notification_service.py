"""通知服务：当前 mock 实现，所有触发点写入 notifications 表（status = MOCKED）。

后续可无侵入替换为阿里云短信 / 126 SMTP 等真实渠道：只需扩展 send() 实现。
匿名用户不接收通知；匿名相关节点不写匿名收件人通知。
"""
from app.constants import Role
from app.db import database as db

CHANNEL_MOCK = "mock"
STATUS_MOCKED = "MOCKED"

INSERT_SQL = """
    INSERT INTO notifications(channel, recipient, subject, content, status, related_type, related_id)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
"""


def add(conn, *, recipient: str, subject: str, content: str,
        related_type: str | None = None, related_id: int | None = None) -> None:
    """写入一条 mock 通知记录。"""
    db.execute(
        INSERT_SQL,
        (CHANNEL_MOCK, recipient, subject, content, STATUS_MOCKED, related_type, related_id),
        conn,
    )


def _active_users_by_role(conn, role: str) -> list[dict]:
    sql = "SELECT id, username, display_name FROM users WHERE role = %s AND is_active = TRUE"
    return db.all(sql, (role,), conn)


def notify_role(conn, role: str, subject: str, content: str,
                related_type: str | None = None, related_id: int | None = None) -> None:
    """按角色通知（每名启用用户一条记录）。"""
    for u in _active_users_by_role(conn, role):
        add(conn, recipient=u["username"], subject=subject, content=content,
            related_type=related_type, related_id=related_id)


def notify_department(conn, department_id: int, subject: str, content: str,
                      related_type: str | None = None, related_id: int | None = None) -> None:
    """通知某部门全部启用负责人。"""
    rows = db.all(
        "SELECT id, username, display_name FROM users "
        "WHERE role = %s AND department_id = %s AND is_active = TRUE",
        (Role.DEPARTMENT, department_id), conn,
    )
    for u in rows:
        add(conn, recipient=u["username"], subject=subject, content=content,
            related_type=related_type, related_id=related_id)
