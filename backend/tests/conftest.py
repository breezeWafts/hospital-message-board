"""pytest 全局配置：测试库创建、迁移、清库、TestClient、种子用户。

运行前提：本机可连接 PostgreSQL。测试库默认：
    postgresql://postgres:postgres@127.0.0.1:5432/hmb_test
可用环境变量 TEST_DATABASE_URL 覆盖。
"""
import os
import shutil
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

TEST_DB = os.environ.get(
    "TEST_DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:5432/hmb_test"
)

# 必须在导入 app 之前设置环境变量
os.environ["DATABASE_URL"] = TEST_DB
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-0123456789")
os.environ.setdefault("CAPTCHA_SECRET", "test-captcha-secret-0123456789")
os.environ["UPLOAD_DIR"] = str(BACKEND_DIR / "test_uploads")
os.environ.setdefault("FRONTEND_BASE_URL", "http://localhost:5173")
os.environ.setdefault("OAUTH2_AUTHORIZE_URL", "https://sso.example.com/authorize")
os.environ.setdefault("OAUTH2_TOKEN_URL", "https://sso.example.com/token")
os.environ.setdefault("OAUTH2_USERINFO_URL", "https://sso.example.com/userinfo")
os.environ.setdefault("OAUTH2_CLIENT_ID", "test-client")
os.environ.setdefault("OAUTH2_CLIENT_SECRET", "test-secret")
os.environ.setdefault("OAUTH2_REDIRECT_URI", "http://localhost:8000/api/auth/oauth2/callback")
# 测试环境放宽防刷阈值，避免套件请求被限流
os.environ["RATE_LIMIT_MAX_REQUESTS"] = "100000"
os.environ["ANON_SUBMIT_COOLDOWN_SECONDS"] = "0"
os.environ["LOGIN_MAX_ATTEMPTS"] = "5"
os.environ["LOGIN_LOCK_MINUTES"] = "15"

import psycopg2
import pytest
from fastapi.testclient import TestClient

from app.core import security
from app.db import database as db
from app.main import app
from scripts.migrate import run as run_migrate

TRUNCATE_TABLES = [
    "audit_logs", "notifications", "evaluations", "reviews", "task_attachments", "tasks",
    "message_attachments", "messages", "oauth_states", "ip_blacklist", "system_configs",
    "users", "departments",
]


def _ensure_test_database():
    """测试库不存在时自动创建（连接到默认 postgres 库执行 CREATE DATABASE）。"""
    try:
        conn = psycopg2.connect(TEST_DB, connect_timeout=5)
        conn.close()
        return
    except psycopg2.OperationalError as e:
        if "does not exist" not in str(e):
            raise
    from urllib.parse import urlparse, urlunparse

    parts = urlparse(TEST_DB)
    dbname = parts.path.lstrip("/")
    admin_url = urlunparse(
        (parts.scheme, parts.netloc, "/postgres", parts.params, parts.query, parts.fragment)
    )
    conn = psycopg2.connect(admin_url, connect_timeout=5)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute(f'CREATE DATABASE "{dbname}" ENCODING \'UTF8\'')
    finally:
        conn.close()


@pytest.fixture(scope="session", autouse=True)
def _database():
    _ensure_test_database()
    run_migrate()
    yield
    shutil.rmtree(os.environ["UPLOAD_DIR"], ignore_errors=True)


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def clean_db():
    with db.tx() as conn:
        for table in TRUNCATE_TABLES:
            db.execute(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE", conn=conn)
    from app.services import config_service

    config_service.invalidate()
    yield


SEED_USERS = [
    ("admin", "admin123", "系统管理员", "admin", None),
    ("principal", "principal123", "院长", "principal", None),
    ("secretary", "secretary123", "院长秘书", "secretary", None),
]


@pytest.fixture(autouse=True)
def seeded(clean_db):
    """默认账号 + 两个部门 + 两名部门负责人。"""
    with db.tx() as conn:
        for name, code in [("门诊部", "OUTPATIENT"), ("后勤保障部", "LOGISTICS")]:
            db.execute(
                "INSERT INTO departments(name, code, is_active) VALUES (%s, %s, TRUE)",
                (name, code), conn,
            )
        dept1 = db.scalar("SELECT id FROM departments WHERE code = 'OUTPATIENT'", conn=conn)
        dept2 = db.scalar("SELECT id FROM departments WHERE code = 'LOGISTICS'", conn=conn)
        for username, password, display_name, role, _ in SEED_USERS:
            db.execute(
                """INSERT INTO users(username, password_hash, display_name, role, is_active,
                                     must_change_password, auth_source)
                   VALUES (%s, %s, %s, %s, TRUE, FALSE, 'local')""",
                (username, security.hash_password(password), display_name, role), conn,
            )
        for username, dept_id in [("dept_user1", dept1), ("dept_user2", dept2)]:
            db.execute(
                """INSERT INTO users(username, password_hash, display_name, role, department_id,
                                     is_active, must_change_password, auth_source)
                   VALUES (%s, %s, %s, 'department', %s, TRUE, FALSE, 'local')""",
                (username, security.hash_password("dept12345"), f"负责人-{username}", dept_id), conn,
            )
    return {
        "departments": {"OUTPATIENT": dept1, "LOGISTICS": dept2},
        "users": {
            "admin": ("admin", "admin123"),
            "principal": ("principal", "principal123"),
            "secretary": ("secretary", "secretary123"),
            "dept_user1": ("dept_user1", "dept12345"),
            "dept_user2": ("dept_user2", "dept12345"),
        },
    }
