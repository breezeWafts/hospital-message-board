"""初始化种子数据（幂等，可重复执行）。

- 默认部门
- 默认账号（本地账号，must_change_password = true，首次登录后必须修改密码）：
    管理员   admin      / admin123
    院长     principal  / principal123
    秘书     secretary  / secretary123
    部门     department / department123   （门诊部）

用法：python -m scripts.seed
"""
import os
import sys
from pathlib import Path

import bcrypt
import psycopg2

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

DEPARTMENTS = [
    ("门诊部", "OUTPATIENT"),
    ("住院部", "INPATIENT"),
    ("后勤保障部", "LOGISTICS"),
    ("药剂科", "PHARMACY"),
    ("检验科", "LABORATORY"),
    ("护理部", "NURSING"),
]

USERS = [
    # username, password, display_name, role, department_code(可空)
    ("admin", "admin123", "系统管理员", "admin", None),
    ("principal", "principal123", "院长", "principal", None),
    ("secretary", "secretary123", "院长秘书", "secretary", None),
    ("department", "department123", "门诊部负责人", "department", "OUTPATIENT"),
]


def _database_url() -> str:
    url = os.environ.get("DATABASE_URL", "")
    if url:
        return url
    env_file = BACKEND_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("DATABASE_URL="):
                return line.split("=", 1)[1].strip()
    raise RuntimeError("未设置 DATABASE_URL 环境变量")


def main() -> None:
    conn = psycopg2.connect(_database_url())
    try:
        with conn.cursor() as cur:
            for name, code in DEPARTMENTS:
                cur.execute(
                    "INSERT INTO departments(name, code) VALUES (%s, %s) ON CONFLICT (code) DO NOTHING",
                    (name, code),
                )
            for username, password, display_name, role, dept_code in USERS:
                cur.execute("SELECT id FROM users WHERE username = %s", (username,))
                if cur.fetchone():
                    continue
                dept_id = None
                if dept_code:
                    cur.execute("SELECT id FROM departments WHERE code = %s", (dept_code,))
                    row = cur.fetchone()
                    dept_id = row[0] if row else None
                password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
                cur.execute(
                    """INSERT INTO users(username, password_hash, display_name, role, department_id,
                       is_active, must_change_password, auth_source)
                       VALUES (%s, %s, %s, %s, %s, TRUE, TRUE, 'local')""",
                    (username, password_hash, display_name, role, dept_id),
                )
        conn.commit()
        print("[seed] 种子数据就绪。")
        print("  默认账号（首次登录后必须修改密码）：")
        for username, password, display_name, role, _ in USERS:
            print(f"    {role:12s} {username:12s} / {password}")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
