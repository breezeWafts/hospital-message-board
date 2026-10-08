"""用户服务：本地账号登录（锁定策略）、密码修改、统一认证(OAuth2)创建/绑定、管理员用户维护。"""
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException

from app.constants import Role
from app.core import security
from app.core.config import get_settings
from app.db import database as db
from app.services import audit_service, config_service

USER_COLS = ("id, username, password_hash, display_name, phone, email, auth_source, "
             "external_user_id, role, department_id, is_active, must_change_password, "
             "failed_attempts, locked_until, created_at, updated_at")


def _with_dept_name(user: dict) -> dict:
    if user and user.get("department_id"):
        row = db.one("SELECT name FROM departments WHERE id = %s", (user["department_id"],))
        user["department_name"] = row["name"] if row else None
    else:
        user["department_name"] = None
    return user


def public_user(user: dict) -> dict:
    """对外输出：绝不暴露 password_hash / external_user_id 等敏感字段。"""
    if not user:
        return user
    return {
        "id": user["id"],
        "username": user["username"],
        "display_name": user.get("display_name"),
        "phone": user.get("phone"),
        "email": user.get("email"),
        "auth_source": user.get("auth_source"),
        "role": user.get("role"),
        "department_id": user.get("department_id"),
        "department_name": user.get("department_name"),
        "is_active": user.get("is_active"),
        "must_change_password": user.get("must_change_password"),
    }


def get_by_id(user_id: int, conn=None) -> dict | None:
    return _with_dept_name(db.one(f"SELECT {USER_COLS} FROM users WHERE id = %s", (user_id,), conn))


def get_by_username(username: str, conn=None) -> dict | None:
    return _with_dept_name(
        db.one(f"SELECT {USER_COLS} FROM users WHERE username = %s", (username,), conn)
    )


def get_by_external_id(external_user_id: str, conn=None) -> dict | None:
    return _with_dept_name(
        db.one(f"SELECT {USER_COLS} FROM users WHERE external_user_id = %s", (external_user_id,), conn)
    )


# ---------------- 登录 ----------------

def _locked(user: dict) -> bool:
    locked_until = user.get("locked_until")
    return bool(locked_until and locked_until > datetime.now(timezone.utc))


def authenticate(username: str, password: str, ip: str | None, ua: str | None) -> dict:
    """本地账号密码登录。失败 5 次锁定 15 分钟；锁定需等自动解锁。"""
    s = get_settings()
    max_attempts = config_service.get_int("login_max_attempts", s.login_max_attempts)
    lock_minutes = config_service.get_int("login_lock_minutes", s.login_lock_minutes)
    with db.tx() as conn:
        user = get_by_username(username, conn)
        if user is None:
            raise HTTPException(status_code=401, detail="账号或密码错误")
        if _locked(user):
            raise HTTPException(
                status_code=423,
                detail={"message": "账号已锁定，请稍后再试", "locked_until": user["locked_until"].isoformat()},
            )
        if not user.get("password_hash"):
            raise HTTPException(status_code=401, detail="该账号使用统一认证登录，无本地密码")
        ok = security.verify_password(password, user["password_hash"])
        if not ok:
            failed = (user.get("failed_attempts") or 0) + 1
            locked_until = None
            if failed >= max_attempts:
                locked_until = datetime.now(timezone.utc) + timedelta(minutes=lock_minutes)
            db.execute(
                "UPDATE users SET failed_attempts = %s, locked_until = %s, updated_at = now() WHERE id = %s",
                (failed, locked_until, user["id"]), conn,
            )
            audit_service.log(
                conn, operator=user, ip=ip, ua=ua, action="LOGIN_FAILED",
            )
            raise HTTPException(
                status_code=401,
                detail=f"账号或密码错误，剩余尝试次数 {max(0, max_attempts - failed)}",
            )
        if not user.get("is_active"):
            raise HTTPException(status_code=403, detail="账号已被禁用，请联系系统管理员")
        db.execute(
            "UPDATE users SET failed_attempts = 0, locked_until = NULL, updated_at = now() WHERE id = %s",
            (user["id"],), conn,
        )
        audit_service.log(conn, operator=user, ip=ip, ua=ua, action="LOGIN_SUCCESS")
        user = get_by_id(user["id"], conn)
    return user


def change_password(user: dict, old_password: str, new_password: str, ip: str | None, ua: str | None) -> None:
    """修改密码：校验旧密码、密码策略、bcrypt 哈希；清除首次改密标记。"""
    if not security.password_policy_ok(new_password):
        raise HTTPException(status_code=400, detail="密码至少 8 位，且必须同时包含字母和数字")
    with db.tx() as conn:
        current = get_by_id(user["id"], conn)
        if current.get("password_hash"):
            if not security.verify_password(old_password, current["password_hash"]):
                raise HTTPException(status_code=400, detail="原密码错误")
        db.execute(
            "UPDATE users SET password_hash = %s, must_change_password = FALSE, updated_at = now() WHERE id = %s",
            (security.hash_password(new_password), user["id"]), conn,
        )
        audit_service.log(conn, operator=user, ip=ip, ua=ua, action="PASSWORD_CHANGED")


# ---------------- 统一认证（OAuth2）----------------

def create_oauth_state(state: str, redirect_uri: str, conn=None) -> None:
    s = get_settings()
    db.execute(
        "INSERT INTO oauth_states(state, redirect_uri, expires_at) "
        "VALUES (%s, %s, now() + (%s || ' seconds')::interval)",
        (state, redirect_uri, s.oauth2_state_ttl_seconds), conn,
    )


def consume_oauth_state(state: str) -> str:
    """校验并消费 state（防 CSRF）。返回 redirect_uri；无效/过期/已用抛 400。"""
    with db.tx() as conn:
        row = db.one(
            "SELECT state, redirect_uri, expires_at, used FROM oauth_states WHERE state = %s FOR UPDATE",
            (state,), conn,
        )
        if row is None:
            raise HTTPException(status_code=400, detail="无效的 state，请重新发起统一认证登录")
        if row["used"]:
            raise HTTPException(status_code=400, detail="state 已被使用，请重新发起统一认证登录")
        if row["expires_at"] < datetime.now(timezone.utc):
            raise HTTPException(status_code=400, detail="state 已过期，请重新发起统一认证登录")
        db.execute("UPDATE oauth_states SET used = TRUE WHERE state = %s", (state,), conn)
        return row["redirect_uri"]


def oauth_login(info: dict, ip: str | None, ua: str | None) -> tuple[dict, bool]:
    """统一认证登录：按 userId 自动创建或绑定本地用户。

    首次登录创建的用户默认 auth_source=oauth2、role 为空、is_active=False，
    等待管理员授权；已绑定用户更新 name/phone/email 并校验本地 is_active 与 role。
    返回 (user, created)。
    """
    external_id = (info.get("userId") or "").strip()
    if not external_id:
        raise HTTPException(status_code=400, detail="统一认证中心未返回 userId")
    name = info.get("name") or ""
    phone = info.get("phone") or ""
    email = info.get("email") or ""
    with db.tx() as conn:
        user = get_by_external_id(external_id, conn)
        created = False
        if user is None:
            username = _dedupe_username(external_id, conn)
            db.execute(
                """INSERT INTO users(username, display_name, phone, email, auth_source,
                                     external_user_id, role, department_id, is_active, must_change_password)
                   VALUES (%s, %s, %s, %s, 'oauth2', %s, NULL, NULL, FALSE, FALSE)""",
                (username, name, phone, email, external_id), conn,
            )
            user = get_by_external_id(external_id, conn)
            created = True
        else:
            db.execute(
                "UPDATE users SET display_name = %s, phone = %s, email = %s, updated_at = now() WHERE id = %s",
                (name, phone, email, user["id"]), conn,
            )
            user = get_by_id(user["id"], conn)
        audit_service.log(
            conn, operator=user if not created else None,
            role=user.get("role") or "anonymous",
            ip=ip, ua=ua, action="OAUTH_LOGIN",
        )
        return user, created


def _dedupe_username(base: str, conn) -> str:
    """username 默认取 userId，冲突时追加后缀。"""
    if get_by_username(base, conn) is None:
        return base
    for i in range(2, 10000):
        candidate = f"{base}_{i}"
        if get_by_username(candidate, conn) is None:
            return candidate
    raise HTTPException(status_code=500, detail="用户名冲突，无法自动创建")


# ---------------- 管理员维护 ----------------

def list_users(search: str | None, page, page_size, conn=None) -> dict:
    p, s, offset, limit = db.page(page, page_size)
    where, params = "", []
    if search:
        where = "WHERE (username LIKE %s ESCAPE '\\\\' OR display_name LIKE %s ESCAPE '\\\\' OR phone LIKE %s ESCAPE '\\\\')"
        like = f"%{db.escape_like(search)}%"
        params = [like, like, like]
    total = db.count(f"SELECT count(*) AS c FROM users {where}", params, conn)
    rows = db.all(
        f"""SELECT u.*, d.name AS department_name FROM users u
            LEFT JOIN departments d ON d.id = u.department_id
            {where} ORDER BY u.id LIMIT %s OFFSET %s""",
        params + [limit, offset], conn,
    )
    items = [public_user(_with_dept_name(r)) for r in rows]
    return {"total": total, "page": p, "page_size": s, "items": items}


def create_user(data: dict, operator: dict, ip, ua) -> dict:
    role = data.get("role")
    _validate_role_department(role, data.get("department_id"))
    password = data.get("password")
    password_hash = None
    must_change = False
    if role and password:
        if not security.password_policy_ok(password):
            raise HTTPException(status_code=400, detail="密码至少 8 位，且必须同时包含字母和数字")
        password_hash = security.hash_password(password)
        must_change = True
    elif role and not password:
        raise HTTPException(status_code=400, detail="创建账号必须设置初始密码")
    with db.tx() as conn:
        if get_by_username(data["username"], conn):
            raise HTTPException(status_code=400, detail="用户名已存在")
        db.execute(
            """INSERT INTO users(username, password_hash, display_name, phone, email, auth_source,
                                 role, department_id, is_active, must_change_password)
               VALUES (%s, %s, %s, %s, %s, 'local', %s, %s, %s, %s)""",
            (data["username"], password_hash, data.get("display_name"), data.get("phone"),
             data.get("email"), role, data.get("department_id"),
             data.get("is_active", True), must_change), conn,
        )
        new_user = get_by_username(data["username"], conn)
        audit_service.log(conn, operator=operator, ip=ip, ua=ua, action="USER_CREATED")
    return new_user


def update_user(user_id: int, data: dict, operator: dict, ip, ua) -> dict:
    """管理员更新用户：角色/部门/启用状态/联系方式/重置密码。统一认证用户由此授权。"""
    with db.tx() as conn:
        target = get_by_id(user_id, conn)
        if target is None:
            raise HTTPException(status_code=404, detail="用户不存在")
        role = data.get("role", target.get("role"))
        dept_id = data.get("department_id", target.get("department_id"))
        _validate_role_department(role, dept_id)
        password_hash = None
        if data.get("password"):
            if not security.password_policy_ok(data["password"]):
                raise HTTPException(status_code=400, detail="密码至少 8 位，且必须同时包含字母和数字")
            password_hash = security.hash_password(data["password"])
        password_hash_sql = ", password_hash = %s, must_change_password = TRUE" if password_hash else ""
        # 参数顺序必须与 SQL 占位符顺序一致：
        # display_name, phone, email, role, department_id, is_active, [password_hash], id
        params: list = [
            data.get("display_name", target.get("display_name")),
            data.get("phone", target.get("phone")),
            data.get("email", target.get("email")),
            role,
            dept_id,
            data.get("is_active", target.get("is_active")),
        ]
        if password_hash:
            params.append(password_hash)
        params.append(user_id)
        db.execute(
            f"""UPDATE users SET display_name = %s, phone = %s, email = %s, role = %s,
                                 department_id = %s, is_active = %s, updated_at = now()
                                 {password_hash_sql}
                 WHERE id = %s""",
            params, conn,
        )
        updated = get_by_id(user_id, conn)
        audit_service.log(conn, operator=operator, ip=ip, ua=ua, action="USER_UPDATED")
    return updated


def _validate_role_department(role: str | None, department_id: int | None) -> None:
    if role and role not in Role.ALL_STAFF:
        raise HTTPException(status_code=400, detail=f"非法角色: {role}")
    if role == Role.DEPARTMENT:
        if not department_id:
            raise HTTPException(status_code=400, detail="部门负责人必须指定部门")
        dept = db.one("SELECT id, is_active FROM departments WHERE id = %s", (department_id,))
        if dept is None:
            raise HTTPException(status_code=400, detail="部门不存在")
        if not dept.get("is_active"):
            raise HTTPException(status_code=400, detail="部门已停用")
