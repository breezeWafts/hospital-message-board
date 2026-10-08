"""匿名 API：提交留言（multipart）、查询（编号+验证码）、评价。"""
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.core.deps import client_ip, client_ua
from app.db import database as db
from app.schemas import AnonymousQueryIn, EvaluateIn
from app.services import attachment_service, message_service

router = APIRouter(prefix="/api/anonymous", tags=["anonymous"])

MAX_FILES = 10


async def _read_files(files: list[UploadFile] | None) -> list[dict]:
    result = []
    if not files:
        return result
    for f in files:
        if f.filename is None or f.filename == "":
            continue
        filename, mime, size, data = await attachment_service.read_file(f)
        result.append({"filename": filename, "mime": mime, "size": size, "data": data})
    return result


@router.post("/messages")
async def submit_message(
    title: str = Form(...),
    content: str = Form(...),
    attachments: list[UploadFile] | None = File(default=None),
    ip: str = Depends(client_ip),
    ua: str = Depends(client_ua),
):
    if attachments is None:
        attachments = []
    if len(attachments) > MAX_FILES:
        raise HTTPException(status_code=400, detail=f"单次最多上传 {MAX_FILES} 个文件")
    files = await _read_files(attachments)
    with db.tx() as conn:
        msg_id, captcha = message_service.create_message(
            conn, title=title, content=content, files=files, ip=ip, ua=ua
        )
    return {
        "id": msg_id,
        "captcha": captcha,
        "message": "提交成功！请务必截图保存留言编号与查询验证码，用于后续查询进度与结果。",
    }


@router.post("/messages/query")
def query_message(body: AnonymousQueryIn, ip: str = Depends(client_ip), ua: str = Depends(client_ua)):
    return message_service.query_anonymous(body.id, body.captcha, ip, ua)


@router.post("/messages/{message_id}/evaluate")
def evaluate_message(message_id: int, body: EvaluateIn,
                     ip: str = Depends(client_ip), ua: str = Depends(client_ua)):
    return message_service.evaluate(message_id, body.captcha, body.satisfied, body.content, ip, ua)
