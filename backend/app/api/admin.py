"""管理员 API：用户/部门维护、系统配置、日志查询、重置验证码锁定、IP 黑名单、统一认证用户授权。"""
from fastapi import APIRouter, Depends, HTTPException, Query

from app.constants import Role
from app.core.deps import client_ip, client_ua, require_roles
from app.db import database as db
from app.schemas import (
    ConfigsUpdateIn,
    DepartmentIn,
    DepartmentUpdateIn,
    ResetCaptchaIn,
    UserCreateIn,
    UserUpdateIn,
)
from app.services import (
    audit_service,
    config_service,
    department_service,
    message_service,
    user_service,
)

router = APIRouter(prefix="/api/admin", tags=["admin"],
                   dependencies=[Depends(require_roles(Role.ADMIN))])


# ---------------- 用户管理（含统一认证用户授权）----------------

@router.get("/users")
def list_users(
    search: str | None = Query(default=None),
    page: int | None = Query(default=1),
    page_size: int | None = Query(default=20),
    _: dict = Depends(require_roles(Role.ADMIN)),
):
    return user_service.list_users(search, page, page_size)


@router.post("/users")
def create_user(body: UserCreateIn, user: dict = Depends(require_roles(Role.ADMIN)),
                ip: str = Depends(client_ip), ua: str = Depends(client_ua)):
    return user_service.public_user(
        user_service.create_user(body.model_dump(), user, ip, ua)
    )


@router.patch("/users/{user_id}")
def update_user(user_id: int, body: UserUpdateIn, user: dict = Depends(require_roles(Role.ADMIN)),
                ip: str = Depends(client_ip), ua: str = Depends(client_ua)):
    """修改角色/部门/启用状态/重置密码；统一认证用户由此完成授权。"""
    return user_service.public_user(
        user_service.update_user(user_id, body.model_dump(exclude_none=True), user, ip, ua)
    )


# ---------------- 部门管理 ----------------

@router.get("/departments")
def list_departments(_: dict = Depends(require_roles(Role.ADMIN))):
    return department_service.list_departments()


@router.post("/departments")
def create_department(body: DepartmentIn, user: dict = Depends(require_roles(Role.ADMIN)),
                      ip: str = Depends(client_ip), ua: str = Depends(client_ua)):
    with db.tx() as conn:
        dept = department_service.create_department(body.name, body.code, conn)
        audit_service.log(conn, operator=user, ip=ip, ua=ua, action="DEPARTMENT_CREATED")
    return dept


@router.patch("/departments/{dept_id}")
def update_department(dept_id: int, body: DepartmentUpdateIn,
                      user: dict = Depends(require_roles(Role.ADMIN)),
                      ip: str = Depends(client_ip), ua: str = Depends(client_ua)):
    with db.tx() as conn:
        dept = department_service.update_department(dept_id, body.name, body.is_active, conn)
        audit_service.log(conn, operator=user, ip=ip, ua=ua, action="DEPARTMENT_UPDATED")
    return dept


# ---------------- 系统配置 ----------------

@router.get("/configs")
def get_configs(_: dict = Depends(require_roles(Role.ADMIN))):
    return {"configs": config_service.all_configs()}


@router.put("/configs")
def update_configs(body: ConfigsUpdateIn, user: dict = Depends(require_roles(Role.ADMIN)),
                   ip: str = Depends(client_ip), ua: str = Depends(client_ua)):
    with db.tx() as conn:
        result = config_service.set_many(body.configs, user["id"], conn)
        audit_service.log(conn, operator=user, ip=ip, ua=ua, action="CONFIG_UPDATED")
    return {"configs": result}


# ---------------- 重置验证码锁定 ----------------

@router.post("/messages/reset-captcha")
def reset_captcha(body: ResetCaptchaIn, user: dict = Depends(require_roles(Role.ADMIN)),
                  ip: str = Depends(client_ip), ua: str = Depends(client_ua)):
    """仅解除锁定：attempts=0、locked_until=NULL；不重新生成验证码、不修改哈希。"""
    return message_service.reset_captcha_lock(user, body.message_id, ip, ua)


# ---------------- 日志查询 ----------------

@router.get("/logs")
def get_logs(
    action: str | None = Query(default=None),
    operator: str | None = Query(default=None),
    role: str | None = Query(default=None),
    message_id: int | None = Query(default=None),
    task_id: int | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    sort: str = Query(default="created_at_desc"),
    page: int | None = Query(default=1),
    page_size: int | None = Query(default=20),
    _: dict = Depends(require_roles(Role.ADMIN)),
):
    return audit_service.query_logs(
        action=action, operator=operator, role=role, message_id=message_id, task_id=task_id,
        date_from=date_from, date_to=date_to, sort=sort, page=page, page_size=page_size,
    )


# ---------------- IP 黑名单（扩展：便于管理员查看/解除）----------------

@router.get("/blacklist")
def get_blacklist(_: dict = Depends(require_roles(Role.ADMIN))):
    rows = db.all(
        "SELECT id, ip, reason, created_at, expires_at FROM ip_blacklist ORDER BY id DESC LIMIT 200"
    )
    return {"items": rows}


@router.delete("/blacklist/{ip}")
def remove_blacklist(ip: str, user: dict = Depends(require_roles(Role.ADMIN)),
                     client_ip_: str = Depends(client_ip), ua: str = Depends(client_ua)):
    deleted = db.execute("DELETE FROM ip_blacklist WHERE ip = %s", (ip,))
    if not deleted:
        raise HTTPException(status_code=404, detail="该 IP 不在黑名单中")
    with db.tx() as conn:
        audit_service.log(conn, operator=user, ip=client_ip_, ua=ua, action="IP_UNBLACKLISTED")
    return {"ok": True}
