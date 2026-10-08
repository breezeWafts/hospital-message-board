"""系统配置服务：system_configs 表优先，settings/.env 兜底，带短时缓存。"""
import threading
import time

from app.constants import (
    DEFAULT_ANON_SUBMIT_COOLDOWN_SECONDS,
    DEFAULT_BLACKLIST_BAN_SECONDS,
    DEFAULT_CAPTCHA_LOCK_DAYS,
    DEFAULT_CAPTCHA_MAX_ATTEMPTS,
    DEFAULT_CAPTCHA_TTL_DAYS,
    DEFAULT_MAX_FILES_PER_SUBMIT,
    DEFAULT_MAX_FILE_SIZE_MB,
    DEFAULT_LOGIN_LOCK_MINUTES,
    DEFAULT_LOGIN_MAX_ATTEMPTS,
    DEFAULT_RATE_LIMIT_MAX_REQUESTS,
    DEFAULT_RATE_LIMIT_WINDOW_SECONDS,
)
from app.core.config import get_settings
from app.db import database as db

CACHE_TTL_SECONDS = 10

_cache: dict[str, str] = {}
_cache_ts: float = 0.0
_lock = threading.Lock()


def _fallbacks() -> dict[str, str]:
    """settings/.env 兜底值。

    注意：不能用 `x or default`，否则 0/空串等合法配置值会被吞掉
    （例如测试环境 ANON_SUBMIT_COOLDOWN_SECONDS=0 关闭冷却）。
    """
    s = get_settings()

    def val(env_value, default):
        return str(env_value if env_value is not None else default)

    return {
        "max_file_size_mb": val(s.max_file_size_mb, DEFAULT_MAX_FILE_SIZE_MB),
        "max_files_per_submit": val(s.max_files_per_submit, DEFAULT_MAX_FILES_PER_SUBMIT),
        "captcha_ttl_days": val(s.captcha_ttl_days, DEFAULT_CAPTCHA_TTL_DAYS),
        "captcha_max_attempts": val(s.captcha_max_attempts, DEFAULT_CAPTCHA_MAX_ATTEMPTS),
        "captcha_lock_days": val(s.captcha_lock_days, DEFAULT_CAPTCHA_LOCK_DAYS),
        "login_max_attempts": val(s.login_max_attempts, DEFAULT_LOGIN_MAX_ATTEMPTS),
        "login_lock_minutes": val(s.login_lock_minutes, DEFAULT_LOGIN_LOCK_MINUTES),
        "rate_limit_max_requests": val(s.rate_limit_max_requests, DEFAULT_RATE_LIMIT_MAX_REQUESTS),
        "rate_limit_window_seconds": val(s.rate_limit_window_seconds, DEFAULT_RATE_LIMIT_WINDOW_SECONDS),
        "blacklist_ban_seconds": val(s.blacklist_ban_seconds, DEFAULT_BLACKLIST_BAN_SECONDS),
        "anon_submit_cooldown_seconds": val(
            s.anon_submit_cooldown_seconds, DEFAULT_ANON_SUBMIT_COOLDOWN_SECONDS
        ),
    }


def invalidate() -> None:
    global _cache, _cache_ts
    with _lock:
        _cache = {}
        _cache_ts = 0.0


def _ensure_cache() -> dict[str, str]:
    global _cache, _cache_ts
    now = time.time()
    with _lock:
        if not _cache or now - _cache_ts > CACHE_TTL_SECONDS:
            rows = db.all("SELECT config_key, config_value FROM system_configs")
            _cache = {r["config_key"]: r["config_value"] for r in rows}
            _cache_ts = now
        return dict(_cache)


def get(key: str, default=None):
    """system_configs 表优先，settings/.env 兜底。"""
    cache = _ensure_cache()
    if key in cache:
        return cache[key]
    return _fallbacks().get(key, default)


def get_int(key: str, default: int) -> int:
    try:
        return int(get(key, default))
    except (TypeError, ValueError):
        return default


def get_float(key: str, default: float) -> float:
    try:
        return float(get(key, default))
    except (TypeError, ValueError):
        return default


def all_configs() -> dict[str, str]:
    """合并返回：DB 已显式配置的键 + 兜底默认键。"""
    merged = dict(_fallbacks())
    merged.update(_ensure_cache())
    return merged


def set_many(pairs: dict[str, str], updated_by: int, conn=None) -> dict[str, str]:
    """批量更新配置（UPSERT），返回更新后的完整配置。

    在调用方事务内（传 conn）时，返回值用同一连接读取，避免读到未提交的
    旧数据；缓存仅失效，待事务提交后由后续 get() 重新读取。
    """
    items = [(k, str(v)) for k, v in pairs.items()]
    sql = """
        INSERT INTO system_configs(config_key, config_value, updated_by, updated_at)
        VALUES (%s, %s, %s, now())
        ON CONFLICT (config_key) DO UPDATE
        SET config_value = EXCLUDED.config_value, updated_by = EXCLUDED.updated_by, updated_at = now()
    """
    db.execute_many(sql, [(k, v, updated_by) for k, v in items], conn)
    invalidate()
    merged = dict(_fallbacks())
    if conn is not None:
        rows = db.all("SELECT config_key, config_value FROM system_configs", conn=conn)
        merged.update({r["config_key"]: r["config_value"] for r in rows})
    else:
        merged.update(_ensure_cache())
    return merged
