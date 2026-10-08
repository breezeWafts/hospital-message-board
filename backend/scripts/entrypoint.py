"""Docker 入口：等待数据库就绪 → 执行迁移 → 写入种子数据 → 启动 uvicorn。

用法：python scripts/entrypoint.py
"""
import os
import subprocess
import sys
import time
from pathlib import Path

import psycopg2

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))


def wait_for_db(timeout: int = 120) -> None:
    url = os.environ["DATABASE_URL"]
    deadline = time.time() + timeout
    while True:
        try:
            conn = psycopg2.connect(url, connect_timeout=5)
            conn.close()
            print("[entrypoint] 数据库就绪。")
            return
        except Exception:
            if time.time() > deadline:
                raise RuntimeError("等待数据库超时")
            print("[entrypoint] 等待数据库 ...")
            time.sleep(3)


def main() -> None:
    wait_for_db()
    from scripts.migrate import run as run_migrate
    run_migrate()
    from scripts.seed import main as run_seed
    run_seed()
    workers = os.environ.get("UVICORN_WORKERS", "2")
    print(f"[entrypoint] 启动 uvicorn (workers={workers}) ...")
    os.execv(
        sys.executable,
        [sys.executable, "-m", "uvicorn", "app.main:app",
         "--host", "0.0.0.0", "--port", "8000", "--workers", workers],
    )


if __name__ == "__main__":
    main()
