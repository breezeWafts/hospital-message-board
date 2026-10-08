"""部门 API：本部门任务列表/详情、上传附件并提交处理。"""
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile

from app.constants import Role
from app.core.deps import client_ip, client_ua, require_roles
from app.services import attachment_service, task_service

router = APIRouter(prefix="/api/department", tags=["department"],
                   dependencies=[Depends(require_roles(Role.DEPARTMENT))])


@router.get("/tasks")
def list_tasks(
    status: str | None = Query(default=None),
    page: int | None = Query(default=1),
    page_size: int | None = Query(default=20),
    sort: str = Query(default="created_at_desc"),
    user: dict = Depends(require_roles(Role.DEPARTMENT)),
):
    return task_service.list_tasks(user, status=status, page=page, page_size=page_size, sort=sort)


@router.get("/tasks/{task_id}")
def get_task(task_id: int, user: dict = Depends(require_roles(Role.DEPARTMENT))):
    return task_service.get_task(task_id, user)


@router.post("/tasks/{task_id}/submit")
async def submit_task(
    task_id: int,
    content: str = Form(...),
    attachments: list[UploadFile] | None = File(default=None),
    user: dict = Depends(require_roles(Role.DEPARTMENT)),
    ip: str = Depends(client_ip),
    ua: str = Depends(client_ua),
):
    """上传附件、填写处理内容、提交。对应任务状态 → REVIEWING。"""
    if attachments is None:
        attachments = []
    if len(attachments) > 10:
        raise HTTPException(status_code=400, detail="单次最多上传 10 个文件")
    files = []
    for f in attachments:
        if f.filename is None or f.filename == "":
            continue
        filename, mime, size, data = await attachment_service.read_file(f)
        files.append({"filename": filename, "mime": mime, "size": size, "data": data})
    return task_service.department_submit(user, task_id, content, files, ip, ua)
