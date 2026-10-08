"""防刷中间件：IP 限流（内存滑动窗口）+ 自动拉黑 + 匿名提交冷却。

- 超阈值自动将 IP 加入 ip_blacklist 表（可配置封禁时长），并写审计日志。
- 匿名提交接口额外冷却（防抖），冷却时长可后台修改。
- 黑名单内存缓存 30 秒刷新一次，避免每请求查库。
- IP 取 X-Forwarded-For 首跳（与 deps.client_ip 一致，适配 Nginx 反代）。
"""
import threading
import time
from collections import defaultdict, deque

from fastapi import Request
from fastapi.responses import JSONResponse

from app.constants import AuditAction, Role
from app.core.config import get_settings
from app.db import database as db
from app.services import audit_service, config_service

_state: dict[str, deque] = defaultdict(deque)
_state_lock = threading.Lock()
_last_submit: dict[str, float] = {}

_blacklist_cache: dict = {"ips": set(), "ts": 0.0}
_blacklist_lock = threading.Lock()

_PRUNE_THRESHOLD = 10000


def _client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _blocked_response(request: Request, status: int, message: str) -> JSONResponse:
    """限流/黑名单响应：补 CORS 头（本中间件位于 CORS 外层）。"""
    origin = request.headers.get("origin")
    s = get_settings()
    resp = JSONResponse(status_code=status, content={"detail": message})
    if origin and origin in s.cors_origin_list:
        resp.headers["Access-Control-Allow-Origin"] = origin
        resp.headers["Access-Control-Allow-Credentials"] = "true"
        resp.headers["Vary"] = "Origin"
    return resp


def _prune() -> None:
    """防止按 IP 计数的字典无限增长：超过阈值时清理空队列与过期提交记录。"""
    now = time.time()
    if len(_state) < _PRUNE_THRESHOLD:
        return
    with _state_lock:
        for ip in [k for k, dq in _state.items() if not dq]:
            _state.pop(ip, None)
        stale = [k for k, t in _last_submit.items() if now - t > 86400]
        for k in stale:
            _last_submit.pop(k, None)
    if len(_state) > _PRUNE_THRESHOLD * 2:  # 极端兜底
        with _state_lock:
            _state.clear()
            _last_submit.clear()


def _is_blacklisted(ip: str) -> bool:
    now = time.time()
    with _blacklist_lock:
        if now - _blacklist_cache["ts"] > 30:
            try:
                rows = db.all(
                    "SELECT ip FROM ip_blacklist WHERE expires_at IS NULL OR expires_at > now()"
                )
                _blacklist_cache["ips"] = {r["ip"] for r in rows}
                _blacklist_cache["ts"] = now
            except Exception:
                pass
        return ip in _blacklist_cache["ips"]


def _ban(ip: str) -> None:
    ban_seconds = config_service.get_int("blacklist_ban_seconds", 86400)
    try:
        with db.tx() as conn:
            db.execute(
                """INSERT INTO ip_blacklist(ip, reason, expires_at)
                   VALUES (%s, %s, now() + (%s || ' seconds')::interval)
                   ON CONFLICT (ip) DO UPDATE
                   SET reason = EXCLUDED.reason, expires_at = EXCLUDED.expires_at""",
                (ip, "请求频率过高，自动拉黑", ban_seconds), conn,
            )
            audit_service.log(
                conn, role=Role.SYSTEM, operator_name="系统", ip=ip,
                action=AuditAction.IP_BLACKLISTED,
            )
    except Exception:
        pass
    with _blacklist_lock:
        _blacklist_cache["ips"].add(ip)


def check_and_limit(request: Request) -> JSONResponse | None:
    if not request.url.path.startswith("/api/"):
        return None
    ip = _client_ip(request)
    if _is_blacklisted(ip):
        return _blocked_response(request, 403, "您的 IP 已被限制，请稍后再试")

    window = config_service.get_int("rate_limit_window_seconds", 60)
    max_req = config_service.get_int("rate_limit_max_requests", 120)
    now = time.time()
    with _state_lock:
        dq = _state[ip]
        while dq and now - dq[0] > window:
            dq.popleft()
        dq.append(now)
        over_limit = len(dq) > max_req
        if over_limit:
            dq.clear()
    if over_limit:
        _ban(ip)
        return _blocked_response(request, 403, "请求过于频繁，您的 IP 已被临时限制")

    if request.method == "POST" and request.url.path == "/api/anonymous/messages":
        cooldown = config_service.get_int("anon_submit_cooldown_seconds", 10)
        last = _last_submit.get(ip, 0.0)
        if now - last < cooldown:
            return _blocked_response(request, 429, "操作过于频繁，请稍后再试")
        _last_submit[ip] = now
    _prune()
    return None
