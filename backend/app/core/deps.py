"""FastAPI 依赖：当前用户、角色鉴权、客户端 IP / UA。"""
from fastapi import Depends, Header, HTTPException, Request

from app.constants import Role
from app.core import security
from app.services import user_service


def get_current_user(authorization: str = Header(default=None)) -> dict:
    """解析 Bearer JWT 并从数据库加载用户（角色/启用状态以数据库为准）。"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录或登录已失效")
    token = authorization[7:].strip()
    try:
        payload = security.decode_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="未登录或登录已失效")
    user = user_service.get_by_id(int(payload.get("sub", 0)))
    if user is None or not user.get("is_active"):
        raise HTTPException(status_code=401, detail="账号不存在或已被禁用")
    if not user.get("role"):
        raise HTTPException(status_code=403, detail="账号尚未授权，请联系系统管理员分配角色")
    return user


def get_optional_user(authorization: str = Header(default=None)) -> dict | None:
    """解析可选用户：匿名访问不报错；token 无效返回 None。"""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    try:
        payload = security.decode_token(authorization[7:].strip())
    except Exception:
        return None
    user = user_service.get_by_id(int(payload.get("sub", 0)))
    if user is None or not user.get("is_active"):
        return None
    return user


def require_roles(*roles: str):
    """角色鉴权依赖工厂：require_roles(Role.PRINCIPAL) 等。"""
    allowed = set(roles)

    def dep(user: dict = Depends(get_current_user)) -> dict:
        if user["role"] not in allowed:
            raise HTTPException(status_code=403, detail="无权访问该接口")
        return user

    return dep


def client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def client_ua(request: Request) -> str:
    return (request.headers.get("user-agent") or "")[:500]
