"""自研轻量连接池 + SQL 执行封装 + SQL 安全工具（单文件，全项目唯一数据库访问层）。

约定：
- 连接池基于 queue.LifoQueue 实现，复用最近归还的连接。
- 不使用 ORM / Repository / Model；业务代码直接写 SQL 并调用 db.* 助手。
- 所有值一律使用 %s 占位符参数化；表名、列名、排序方向使用白名单映射，
  禁止接受用户原始输入。
- 每次 execute 只允许一条 SQL（禁止多语句）。
- LIKE 查询必须配合 escape_like() 与 ESCAPE 子句。
- LIMIT / OFFSET 通过 page() 强制 int 并限制上限。
"""
from __future__ import annotations

import queue
import threading
from contextlib import contextmanager

import psycopg2
from psycopg2 import extensions
from psycopg2.extras import RealDictCursor

from app.core.config import get_settings

_pool: queue.LifoQueue | None = None
_pool_lock = threading.Lock()
_created = 0


def init_pool() -> None:
    global _pool
    s = get_settings()
    _pool = queue.LifoQueue(maxsize=s.pool_max_size)


def _new_conn():
    global _created
    conn = psycopg2.connect(get_settings().database_url, cursor_factory=RealDictCursor)
    conn.autocommit = False
    with _pool_lock:
        _created += 1  # 连接成功后再计数，避免失败虚增
    return conn


def acquire():
    """从池中取出连接（优先复用最近归还的），不足时新建（不超过上限）。"""
    if _pool is None:
        init_pool()
    try:
        return _pool.get_nowait()
    except queue.Empty:
        with _pool_lock:
            if _created < get_settings().pool_max_size:
                return _new_conn()
        try:
            return _pool.get(timeout=15)
        except queue.Empty:
            raise RuntimeError("数据库连接池已耗尽，请稍后重试或调大 POOL_MAX_SIZE")


def _destroy(conn) -> None:
    global _created
    try:
        conn.close()
    except Exception:
        pass
    with _pool_lock:
        _created = max(0, _created - 1)


def release(conn) -> None:
    """归还连接：回滚未完成事务；池满或连接损坏则直接关闭。"""
    if conn is None or conn.closed:
        return
    try:
        if conn.get_transaction_status() != extensions.TRANSACTION_STATUS_IDLE:
            conn.rollback()
        try:
            _pool.put_nowait(conn)
        except queue.Full:
            _destroy(conn)
    except Exception:
        _destroy(conn)


def close_pool() -> None:
    global _pool, _created
    if _pool is None:
        return
    while True:
        try:
            c = _pool.get_nowait()
            try:
                c.close()
            except Exception:
                pass
        except queue.Empty:
            break
    with _pool_lock:
        _created = 0


@contextmanager
def tx():
    """事务上下文：提交 / 回滚 / 归还连接。服务层业务函数通过 conn 参数传递同一连接。"""
    conn = acquire()
    try:
        yield conn
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        release(conn)


def _run(conn, sql: str, params, transform):
    with conn.cursor() as cur:
        cur.execute(sql, params or ())  # 单条 SQL；全部参数化
        return transform(cur)


def one(sql: str, params=None, conn=None) -> dict | None:
    if conn is not None:
        return _run(conn, sql, params, lambda c: c.fetchone())
    with tx() as c:
        return _run(c, sql, params, lambda cur: cur.fetchone())


def all(sql: str, params=None, conn=None) -> list[dict]:
    if conn is not None:
        return _run(conn, sql, params, lambda c: c.fetchall())
    with tx() as c:
        return _run(c, sql, params, lambda cur: cur.fetchall())


def _first_value(row):
    return None if row is None else next(iter(row.values()))


def scalar(sql: str, params=None, conn=None):
    if conn is not None:
        return _run(conn, sql, params, lambda c: _first_value(c.fetchone()))
    with tx() as c:
        return _run(c, sql, params, lambda cur: _first_value(cur.fetchone()))


def count(sql: str, params=None, conn=None) -> int:
    return int(scalar(sql, params, conn) or 0)


def execute(sql: str, params=None, conn=None) -> int:
    """执行写操作，返回受影响行数。"""
    if conn is not None:
        return _run(conn, sql, params, lambda c: c.rowcount)
    with tx() as c:
        return _run(c, sql, params, lambda cur: cur.rowcount)


def execute_many(sql: str, seq_of_params, conn=None) -> None:
    def _do(c):
        with c.cursor() as cur:
            cur.executemany(sql, seq_of_params)

    if conn is not None:
        _do(conn)
    else:
        with tx() as c:
            _do(c)


# ---------------- SQL 安全工具 ----------------

def escape_like(value: str | None) -> str:
    """LIKE 查询转义：\\、%、_，配合 ESCAPE '\\\\' 使用。"""
    if value is None:
        return ""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def in_placeholders(values) -> str:
    """动态 IN 子句：按参数个数生成 %s 占位符（配合参数列表展开）。"""
    if not values:
        raise ValueError("IN 子句参数不能为空")
    return ", ".join(["%s"] * len(values))


def page(page, size, max_size: int = 100):
    """LIMIT / OFFSET 强制 int 转换并限制上限，返回 (page, size, offset, limit)。"""
    try:
        p = int(page or 1)
    except (TypeError, ValueError):
        p = 1
    try:
        s = int(size or 20)
    except (TypeError, ValueError):
        s = 20
    p = max(1, p)
    s = max(1, min(s, max_size))
    return p, s, (p - 1) * s, s


def whitelist_sort(raw: str | None, allowed: dict[str, str], default: str = "id") -> str:
    """排序字段白名单映射：禁止接受用户原始输入拼接 SQL。"""
    if not raw:
        return default
    return allowed.get(raw, default)
