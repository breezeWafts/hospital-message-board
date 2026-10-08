"""部门服务：部门维护与查询。"""
from fastapi import HTTPException

from app.db import database as db


def list_departments(conn=None) -> list[dict]:
    return db.all(
        "SELECT id, name, code, is_active, created_at, updated_at FROM departments ORDER BY id", conn=conn
    )


def get_department(dept_id: int, conn=None) -> dict | None:
    return db.one(
        "SELECT id, name, code, is_active, created_at, updated_at FROM departments WHERE id = %s",
        (dept_id,), conn,
    )


def create_department(name: str, code: str, conn=None) -> dict:
    if db.one("SELECT id FROM departments WHERE code = %s", (code,), conn):
        raise HTTPException(status_code=400, detail="部门编码已存在")
    db.execute("INSERT INTO departments(name, code) VALUES (%s, %s)", (name, code), conn)
    return get_department(
        db.scalar("SELECT id FROM departments WHERE code = %s", (code,), conn), conn
    )


def update_department(dept_id: int, name: str | None, is_active: bool | None, conn=None) -> dict:
    dept = get_department(dept_id, conn)
    if dept is None:
        raise HTTPException(status_code=404, detail="部门不存在")
    new_name = name if name is not None else dept["name"]
    new_active = is_active if is_active is not None else dept["is_active"]
    db.execute(
        "UPDATE departments SET name = %s, is_active = %s, updated_at = now() WHERE id = %s",
        (new_name, new_active, dept_id), conn,
    )
    return get_department(dept_id, conn)
