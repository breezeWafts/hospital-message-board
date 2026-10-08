"""应用配置：.env 环境变量兜底；system_configs 表为后台可改配置（见 config_service）。"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # 数据库
    database_url: str = "postgresql://postgres:postgres@127.0.0.1:5432/hospital_board"
    pool_min_size: int = 2
    pool_max_size: int = 10

    # JWT
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 720

    # 验证码
    captcha_secret: str = "dev-captcha-secret"
    captcha_ttl_days: int = 30
    captcha_max_attempts: int = 5
    captcha_lock_days: int = 30

    # 附件
    upload_dir: str = "./uploads"
    max_file_size_mb: int = 20
    max_files_per_submit: int = 10

    # 前端 / CORS
    frontend_base_url: str = "http://localhost:5173"
    cors_origins: str = "http://localhost:5173,http://localhost:8080"

    # 登录锁定
    login_max_attempts: int = 5
    login_lock_minutes: int = 15

    # 防刷
    rate_limit_max_requests: int = 120
    rate_limit_window_seconds: int = 60
    blacklist_ban_seconds: int = 86400
    anon_submit_cooldown_seconds: int = 10

    # 统一认证中心（自定义 OAuth2 授权码模式）
    oauth2_authorize_url: str = ""
    oauth2_token_url: str = ""
    oauth2_userinfo_url: str = ""
    oauth2_client_id: str = ""
    oauth2_client_secret: str = ""
    oauth2_redirect_uri: str = "http://localhost:8000/api/auth/oauth2/callback"
    oauth2_scope: str = ""
    oauth2_state_ttl_seconds: int = 600

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
