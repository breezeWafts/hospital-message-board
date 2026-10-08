"""附件下载 API：全部经过后端鉴权；Nginx 不直接暴露附件存储目录。

可见性规则（v2.2 第九节）：
- 秘书/管理员：全部
- 院长：匿名留言附件在秘书审核通过后可见；任务附件在该任务审核通过后可见
- 部门：仅本部门任务相关附件
- 匿名用户：仅自身留言相关且任务已通过的附件（凭匿名下载令牌，短时效）
"""
import os

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from app.constants import MessageStatus, Role, SecretaryReview, TaskStatus
from app.core import security
from app.core.deps import get_optional_user
from app.services import attachment_service

router = APIRouter(prefix="/api/attachments", tags=["attachments"])


def _respond(row: dict) -> FileResponse:
    if row is None:
        raise HTTPException(status_code=404, detail="附件不存在")
    path = attachment_service.absolute_path(row["stored_path"])
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="附件文件不存在")
    return FileResponse(
        path,
        filename=row["original_name"],
        media_type=row.get("mime_type") or "application/octet-stream",
    )


@router.get("/message/{att_id}")
def download_message_attachment(
    att_id: int,
    anon_token: str | None = Query(default=None),
    user: dict | None = Depends(get_optional_user),
):
    row = attachment_service.get_message_attachment(att_id)
    if row is None:
        raise HTTPException(status_code=404, detail="附件不存在")
    if user is not None:
        role = user["role"]
        if role in (Role.SECRETARY, Role.ADMIN):
            return _respond(row)
        if role == Role.PRINCIPAL:
            if row["secretary_review_result"] == SecretaryReview.APPROVED:
                return _respond(row)
            raise HTTPException(status_code=403, detail="附件尚未通过秘书审核，不可查看")
        raise HTTPException(status_code=403, detail="无权查看该附件")
    # 匿名：短时效签名令牌 + 留言必须已完成/归档
    if anon_token:
        verified = security.verify_anon_token(anon_token)
        if (verified and verified == (att_id, row["message_id"])
                and row["message_status"] in MessageStatus.ANON_VIEWABLE):
            return _respond(row)
    raise HTTPException(status_code=403, detail="无权下载该附件")


@router.get("/task/{att_id}")
def download_task_attachment(
    att_id: int,
    anon_token: str | None = Query(default=None),
    user: dict | None = Depends(get_optional_user),
):
    row = attachment_service.get_task_attachment(att_id)
    if row is None:
        raise HTTPException(status_code=404, detail="附件不存在")
    if user is not None:
        role = user["role"]
        if role in (Role.SECRETARY, Role.ADMIN):
            return _respond(row)
        if role == Role.PRINCIPAL:
            if row["task_status"] == TaskStatus.APPROVED:
                return _respond(row)
            raise HTTPException(status_code=403, detail="任务尚未通过秘书审核，附件不可查看")
        if role == Role.DEPARTMENT:
            if row["department_id"] == user.get("department_id"):
                return _respond(row)
            raise HTTPException(status_code=403, detail="仅可查看本部门任务附件")
        raise HTTPException(status_code=403, detail="无权查看该附件")
    # 匿名：仅自身留言相关且任务已通过的附件
    if anon_token:
        verified = security.verify_anon_token(anon_token)
        if (verified and verified == (att_id, row["message_id"])
                and row["task_status"] == TaskStatus.APPROVED
                and row["message_status"] in MessageStatus.ANON_VIEWABLE):
            return _respond(row)
    raise HTTPException(status_code=403, detail="无权下载该附件")
