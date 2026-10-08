"""附件服务：上传校验、存储（YYYY/MM/DD/uuid.ext）、下载鉴权查询。

附件下载必须经过后端鉴权，Nginx 不直接暴露附件存储目录。
"""
import hashlib
import os
import uuid
from datetime import datetime

from fastapi import HTTPException, UploadFile

from app.constants import ALLOWED_EXTENSIONS, BLOCKED_EXTENSIONS
from app.core.config import get_settings
from app.db import database as db
from app.services import config_service


def _ext_of(filename: str) -> str:
    if "." not in filename:
        return ""
    return filename.rsplit(".", 1)[1].lower()


def validate_file(filename: str, size: int, count_so_far: int) -> None:
    """双保险拦截：白名单校验 + 禁止类型黑名单；大小与数量限制可后台修改。"""
    max_size_mb = config_service.get_int("max_file_size_mb", 20)
    max_files = config_service.get_int("max_files_per_submit", 10)
    ext = _ext_of(filename)
    if ext in BLOCKED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"禁止上传该类型文件: .{ext}")
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: .{ext}")
    if size > max_size_mb * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"单文件不能超过 {max_size_mb} MB")
    if count_so_far + 1 > max_files:
        raise HTTPException(status_code=400, detail=f"单次最多上传 {max_files} 个文件")


async def read_file(file: UploadFile) -> tuple[str, str, int, bytes]:
    """读取上传文件内容，返回 (原始文件名, mime, 大小, 内容)。"""
    data = await file.read()
    filename = file.filename or "unnamed"
    mime = file.content_type or "application/octet-stream"
    return filename, mime, len(data), data


def store_bytes(data: bytes, ext: str) -> str:
    """按 YYYY/MM/DD/uuid.ext 存储，返回相对路径（不含原始文件名）。"""
    s = get_settings()
    now = datetime.now()
    rel_dir = os.path.join(str(now.year), f"{now.month:02d}", f"{now.day:02d}")
    abs_dir = os.path.join(s.upload_dir, rel_dir)
    os.makedirs(abs_dir, exist_ok=True)
    rel_path = os.path.join(rel_dir, f"{uuid.uuid4().hex}.{ext or 'bin'}")
    abs_path = os.path.join(s.upload_dir, rel_path)
    with open(abs_path, "wb") as f:
        f.write(data)
    return rel_path.replace(os.sep, "/")


def sha256_of(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def absolute_path(stored_path: str) -> str:
    return os.path.join(get_settings().upload_dir, stored_path)


def remove_stored(stored_paths: list[str]) -> None:
    """删除已落盘文件（事务回滚时清理孤儿附件，尽力而为）。"""
    for p in stored_paths or []:
        try:
            os.remove(absolute_path(p))
        except OSError:
            pass


# ---------------- 下载鉴权查询 ----------------

def get_message_attachment(att_id: int, conn=None):
    """查询留言附件并附带留言状态信息（供鉴权）。"""
    return db.one(
        """SELECT ma.id, ma.message_id, ma.original_name, ma.stored_path, ma.mime_type,
                  ma.size_bytes, ma.sha256, ma.created_at,
                  m.status AS message_status, m.secretary_review_result
           FROM message_attachments ma JOIN messages m ON m.id = ma.message_id
           WHERE ma.id = %s""",
        (att_id,), conn,
    )


def get_task_attachment(att_id: int, conn=None):
    """查询任务附件并附带任务/留言/部门信息（供鉴权）。"""
    return db.one(
        """SELECT ta.id, ta.task_id, ta.original_name, ta.stored_path, ta.mime_type,
                  ta.size_bytes, ta.sha256, ta.created_at, ta.uploaded_by,
                  t.status AS task_status, t.message_id, t.department_id,
                  m.status AS message_status
           FROM task_attachments ta
           JOIN tasks t ON t.id = ta.task_id
           JOIN messages m ON m.id = t.message_id
           WHERE ta.id = %s""",
        (att_id,), conn,
    )
