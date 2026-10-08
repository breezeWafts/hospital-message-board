"""安全工具：bcrypt 密码哈希、JWT、验证码哈希、OAuth2 state、匿名下载令牌。"""
import base64
import hashlib
import hmac
import secrets
import time
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import get_settings


# ---------------- 密码 ----------------

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    if not password_hash:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def password_policy_ok(password: str) -> bool:
    """密码策略：至少 8 位，必须包含字母和数字。"""
    if len(password) < 8:
        return False
    has_alpha = any(c.isalpha() for c in password)
    has_digit = any(c.isdigit() for c in password)
    return has_alpha and has_digit


# ---------------- JWT ----------------

def create_access_token(user: dict) -> str:
    s = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user["id"]),
        "username": user.get("username"),
        "role": user.get("role"),
        "department_id": user.get("department_id"),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=s.jwt_expire_minutes)).timestamp()),
    }
    return jwt.encode(payload, s.jwt_secret, algorithm=s.jwt_algorithm)


def decode_token(token: str) -> dict:
    s = get_settings()
    return jwt.decode(token, s.jwt_secret, algorithms=[s.jwt_algorithm])


# ---------------- 匿名查询验证码（只存哈希：sha256 + secret）----------------

def generate_captcha() -> str:
    """6 位随机数字。"""
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_captcha(captcha: str) -> str:
    return hashlib.sha256(f"{captcha}:{get_settings().captcha_secret}".encode("utf-8")).hexdigest()


def verify_captcha(captcha: str, captcha_hash: str) -> bool:
    return hmac.compare_digest(hash_captcha(captcha), captcha_hash)


# ---------------- OAuth2 state（防 CSRF，state 本身存 oauth_states 表）----------------

def generate_oauth_state() -> str:
    return secrets.token_urlsafe(32)


# ---------------- 匿名附件下载令牌（短时效、HMAC 签名）----------------

def sign_anon_token(att_id: int, message_id: int, ttl_seconds: int = 600) -> str:
    payload = f"{att_id}:{message_id}:{int(time.time()) + ttl_seconds}"
    sig = hmac.new(
        get_settings().captcha_secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    b64 = base64.urlsafe_b64encode(payload.encode("utf-8")).decode("utf-8")
    return f"{b64}.{sig}"


def verify_anon_token(token: str):
    """返回 (att_id, message_id)，无效或过期返回 None。"""
    try:
        b64, sig = token.rsplit(".", 1)
        payload = base64.urlsafe_b64decode(b64.encode("utf-8")).decode("utf-8")
        expect = hmac.new(
            get_settings().captcha_secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(sig, expect):
            return None
        att_id_s, message_id_s, exp_s = payload.split(":")
        att_id, message_id, exp = int(att_id_s), int(message_id_s), int(exp_s)
        if time.time() > exp:
            return None
        return att_id, message_id
    except Exception:
        return None
