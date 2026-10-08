"""认证 API：本地账号登录、修改密码、当前用户、统一认证 OAuth2（授权码模式）。"""
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse

from app.constants import Role
from app.core import security
from app.core.config import get_settings
from app.core.deps import client_ip, client_ua, get_current_user, require_roles
from app.schemas import ChangePasswordIn, LoginIn
from app.services import config_service, user_service

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _oauth2_settings() -> dict:
    s = get_settings()
    return {
        "authorize_url": config_service.get("oauth2_authorize_url", s.oauth2_authorize_url) or "",
        "token_url": config_service.get("oauth2_token_url", s.oauth2_token_url) or "",
        "userinfo_url": config_service.get("oauth2_userinfo_url", s.oauth2_userinfo_url) or "",
        "client_id": config_service.get("oauth2_client_id", s.oauth2_client_id) or "",
        "client_secret": config_service.get("oauth2_client_secret", s.oauth2_client_secret) or "",
        "redirect_uri": config_service.get("oauth2_redirect_uri", s.oauth2_redirect_uri) or "",
        "scope": config_service.get("oauth2_scope", s.oauth2_scope) or "",
    }


@router.post("/login")
def login(body: LoginIn, ip: str = Depends(client_ip), ua: str = Depends(client_ua)):
    user = user_service.authenticate(body.username, body.password, ip, ua)
    token = security.create_access_token(user)
    return {"token": token, "user": user_service.public_user(user)}


@router.post("/change-password")
def change_password(body: ChangePasswordIn, user: dict = Depends(get_current_user),
                    ip: str = Depends(client_ip), ua: str = Depends(client_ua)):
    user_service.change_password(user, body.old_password, body.new_password, ip, ua)
    return {"ok": True}


@router.get("/me")
def me(user: dict = Depends(get_current_user)):
    return user_service.public_user(user)


@router.get("/oauth2/login")
def oauth2_login(redirect_uri: str = Query(default="")):
    """跳转到统一认证中心授权页；state 存入 oauth_states 表防 CSRF。"""
    o = _oauth2_settings()
    if not o["authorize_url"] or not o["client_id"]:
        raise HTTPException(status_code=501, detail="统一认证中心未配置（OAUTH2_* 环境变量或系统配置）")
    state = security.generate_oauth_state()
    user_service.create_oauth_state(state, redirect_uri)
    params = {
        "response_type": "code",
        "client_id": o["client_id"],
        "redirect_uri": o["redirect_uri"],
        "state": state,
    }
    if o["scope"]:
        params["scope"] = o["scope"]
    sep = "&" if "?" in o["authorize_url"] else "?"
    return RedirectResponse(url=o["authorize_url"] + sep + urlencode(params))


@router.get("/oauth2/callback")
def oauth2_callback(code: str = Query(...), state: str = Query(...),
                    ip: str = Depends(client_ip), ua: str = Depends(client_ua)):
    """接收授权码：后端完成 code 换 token 与 userinfo 获取，创建/绑定本地用户并签发本地 JWT。"""
    s = get_settings()
    front_url = s.frontend_base_url.rstrip("/") + "/oauth2/result"
    try:
        user_service.consume_oauth_state(state)  # 校验 state，防 CSRF
        o = _oauth2_settings()
        token_resp = httpx.post(
            o["token_url"],
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": o["client_id"],
                "client_secret": o["client_secret"],
                "redirect_uri": o["redirect_uri"],
            },
            timeout=15,
        )
        if token_resp.status_code >= 400:
            return RedirectResponse(url=front_url + "?" + urlencode({"error": "统一认证中心拒绝授权"}))
        access_token = token_resp.json().get("access_token")
        if not access_token:
            return RedirectResponse(url=front_url + "?" + urlencode({"error": "no_token"}))
        info_resp = httpx.get(
            o["userinfo_url"], headers={"Authorization": f"Bearer {access_token}"}, timeout=15
        )
        if info_resp.status_code >= 400:
            return RedirectResponse(url=front_url + "?" + urlencode({"error": "userinfo_failed"}))
        info = info_resp.json()
        user, created = user_service.oauth_login(
            {"userId": info.get("userId"), "name": info.get("name"),
             "phone": info.get("phone"), "email": info.get("email")},
            ip, ua,
        )
        if user.get("is_active") and user.get("role"):
            token = security.create_access_token(user)
            return RedirectResponse(
                url=front_url + "?" + urlencode(
                    {"token": token, "pending": "0", "username": user["username"]}
                )
            )
        # 统一认证首次创建默认未授权：等待管理员分配角色、部门并启用
        return RedirectResponse(
            url=front_url + "?" + urlencode({"pending": "1", "username": user["username"]})
        )
    except HTTPException as e:
        detail = e.detail if isinstance(e.detail, str) else str(e.detail)
        return RedirectResponse(url=front_url + "?" + urlencode({"error": detail}))
    except Exception:
        return RedirectResponse(url=front_url + "?" + urlencode({"error": "oauth_failed"}))
