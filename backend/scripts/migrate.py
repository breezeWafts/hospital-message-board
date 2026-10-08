"""自研数据库迁移器（不使用 Alembic）。

- 迁移文件：migrations/Vxxx__*.sql，按版本号升序应用。
- 记录表：schema_migrations（version / filename / checksum / applied_at）。
- 已应用的迁移校验 checksum（文件被修改会报错，保证历史一致性）。
- 每个迁移文件在单独事务中整体执行（DDL 原子性由 PostgreSQL 保证）。

说明：迁移器将整个 SQL 文件作为一批执行（psycopg2 简单查询协议允许批处理）；
业务代码“每次 execute 只允许一条 SQL”的约定不适用于迁移文件本身。

用法：
    python -m scripts.migrate            # 应用所有未应用的迁移
    python -m scripts.migrate status     # 查看状态
"""
import hashlib
import os
import re
import sys
from pathlib import Path

import psycopg2

BACKEND_DIR = Path(__file__).resolve().parent.parent
MIGRATIONS_DIR = BACKEND_DIR / "migrations"
VERSION_RE = re.compile(r"^V(\d{3,})__.+\.sql$")

CREATE_SCHEMA_MIGRATIONS = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    checksum TEXT NOT NULL,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
)
"""


def _database_url() -> str:
    url = os.environ.get("DATABASE_URL", "")
    if url:
        return url
    # 尝试读取 .env（迁移器不依赖 pydantic-settings 也行，但直接复用更省事）
    env_file = BACKEND_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("DATABASE_URL="):
                return line.split("=", 1)[1].strip()
    raise RuntimeError("未设置 DATABASE_URL 环境变量")


def _list_migration_files() -> list[tuple[str, str, Path]]:
    files = []
    for p in sorted(MIGRATIONS_DIR.glob("*.sql")):
        m = VERSION_RE.match(p.name)
        if not m:
            raise RuntimeError(f"迁移文件名不符合 Vxxx__*.sql 格式: {p.name}")
        files.append((m.group(1), p.name, p))
    if not files:
        raise RuntimeError(f"迁移目录没有 SQL 文件: {MIGRATIONS_DIR}")
    return files


def _checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run() -> int:
    conn = psycopg2.connect(_database_url())
    conn.autocommit = False
    applied_count = 0
    try:
        with conn.cursor() as cur:
            cur.execute(CREATE_SCHEMA_MIGRATIONS)
            cur.execute("SELECT version, filename, checksum FROM schema_migrations")
            applied = {row[0]: (row[1], row[2]) for row in cur.fetchall()}

            for version, filename, path in _list_migration_files():
                if version in applied:
                    old_name, old_cs = applied[version]
                    new_cs = _checksum(path)
                    if old_name != filename or old_cs != new_cs:
                        raise RuntimeError(
                            f"已应用的迁移 {version} 被修改（checksum 不一致）: {filename}"
                        )
                    continue
                cs = _checksum(path)
                print(f"[migrate] 应用 {filename} ...")
                cur.execute(path.read_text(encoding="utf-8"))  # 整个文件一批执行
                cur.execute(
                    "INSERT INTO schema_migrations(version, filename, checksum) VALUES (%s, %s, %s)",
                    (version, filename, cs),
                )
                applied_count += 1
        conn.commit()
        print(f"[migrate] 完成，本次应用 {applied_count} 个迁移。")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return applied_count


def status() -> int:
    conn = psycopg2.connect(_database_url())
    try:
        with conn.cursor() as cur:
            cur.execute(CREATE_SCHEMA_MIGRATIONS)
            cur.execute("SELECT version, filename FROM schema_migrations ORDER BY version")
            applied = {row[0]: row[1] for row in cur.fetchall()}
            for version, filename, _ in _list_migration_files():
                mark = "applied" if version in applied else "pending"
                print(f"  V{version}  {filename}  [{mark}]")
    finally:
        conn.close()
    return 0


def main() -> None:
    args = sys.argv[1:]
    if args and args[0] == "status":
        sys.exit(status())
    run()
    sys.exit(0)


if __name__ == "__main__":
    main()
