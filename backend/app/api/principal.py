"""院长 API：批示、最终确认、驳回；留言列表（批示视图/待确认视图/历史）。"""
from fastapi import APIRouter, Depends, Query

from app.constants import Role
from app.core.deps import client_ip, client_ua, require_roles
from app.schemas import InstructionIn, PrincipalRejectIn
from app.services import message_service, task_service

router = APIRouter(prefix="/api/principal", tags=["principal"],
                   dependencies=[Depends(require_roles(Role.PRINCIPAL))])


@router.get("/messages")
def list_messages(
    status: str | None = Query(default=None),
    view: str = Query(default="", description="instruction=待批示 / confirm=待最终确认 / all=全部"),
    search: str | None = Query(default=None),
    page: int | None = Query(default=1),
    page_size: int | None = Query(default=20),
    sort: str = Query(default="created_at_desc"),
    user: dict = Depends(require_roles(Role.PRINCIPAL)),
):
    effective_view = view or ("all" if status else "instruction")
    return message_service.list_messages(
        user, status=status, view=effective_view, search=search,
        page=page, page_size=page_size, sort=sort,
    )


@router.get("/messages/{message_id}")
def get_message(message_id: int, user: dict = Depends(require_roles(Role.PRINCIPAL))):
    return message_service.get_detail(message_id, user)


@router.post("/messages/{message_id}/instruction")
def instruction(message_id: int, body: InstructionIn,
                user: dict = Depends(require_roles(Role.PRINCIPAL)),
                ip: str = Depends(client_ip), ua: str = Depends(client_ua)):
    """批示并通知秘书分解任务。"""
    return message_service.principal_instruction(user, message_id, body.instruction, ip, ua)


@router.post("/messages/{message_id}/confirm")
def confirm(message_id: int, user: dict = Depends(require_roles(Role.PRINCIPAL)),
            ip: str = Depends(client_ip), ua: str = Depends(client_ua)):
    """最终确认完成。"""
    return message_service.principal_confirm(user, message_id, ip, ua)


@router.post("/messages/{message_id}/reject")
def reject(message_id: int, body: PrincipalRejectIn,
           user: dict = Depends(require_roles(Role.PRINCIPAL)),
           ip: str = Depends(client_ip), ua: str = Depends(client_ua)):
    """确认不通过，驳回到秘书。"""
    return message_service.principal_reject(user, message_id, body.comment, ip, ua)


@router.get("/tasks/{task_id}")
def get_task(task_id: int, user: dict = Depends(require_roles(Role.PRINCIPAL))):
    return task_service.get_task(task_id, user)
