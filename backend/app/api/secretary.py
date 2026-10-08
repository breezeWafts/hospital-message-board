"""秘书 API：审核留言、分派任务、逐任务审核、归档、任务列表。"""
from fastapi import APIRouter, Depends, Query

from app.constants import Role
from app.core.deps import client_ip, client_ua, require_roles
from app.schemas import AssignTasksIn, SecretaryReviewIn, TaskReviewIn
from app.services import department_service, message_service, task_service

router = APIRouter(prefix="/api/secretary", tags=["secretary"],
                   dependencies=[Depends(require_roles(Role.SECRETARY))])


@router.get("/departments")
def list_departments(_: dict = Depends(require_roles(Role.SECRETARY))):
    """启用中的部门列表（分派任务下拉框用；实现补充接口）。"""
    return [d for d in department_service.list_departments() if d["is_active"]]


@router.get("/messages")
def list_messages(
    status: str | None = Query(default=None),
    search: str | None = Query(default=None),
    page: int | None = Query(default=1),
    page_size: int | None = Query(default=20),
    sort: str = Query(default="created_at_desc"),
    user: dict = Depends(require_roles(Role.SECRETARY)),
):
    return message_service.list_messages(
        user, status=status, view="all", search=search,
        page=page, page_size=page_size, sort=sort,
    )


@router.get("/messages/{message_id}")
def get_message(message_id: int, user: dict = Depends(require_roles(Role.SECRETARY))):
    return message_service.get_detail(message_id, user)


@router.post("/messages/{message_id}/review")
def review_message(message_id: int, body: SecretaryReviewIn,
                   user: dict = Depends(require_roles(Role.SECRETARY)),
                   ip: str = Depends(client_ip), ua: str = Depends(client_ua)):
    """审核留言：APPROVED 通过（进入待院长批示）/ REJECTED、REFUSED 驳回（必须填写原因）。"""
    return message_service.secretary_review(user, message_id, body.result, body.comment, ip, ua)


@router.post("/messages/{message_id}/tasks/assign")
def assign_tasks(message_id: int, body: AssignTasksIn,
                 user: dict = Depends(require_roles(Role.SECRETARY)),
                 ip: str = Depends(client_ip), ua: str = Depends(client_ua)):
    """将留言分解为一个或多个部门任务并分派；也用于驳回后的二次分派。"""
    return message_service.assign_tasks(user, message_id, [t.model_dump() for t in body.tasks], ip, ua)


@router.get("/tasks")
def list_tasks(
    status: str | None = Query(default=None),
    message_id: int | None = Query(default=None),
    page: int | None = Query(default=1),
    page_size: int | None = Query(default=20),
    sort: str = Query(default="created_at_desc"),
    user: dict = Depends(require_roles(Role.SECRETARY)),
):
    return task_service.list_tasks(
        user, status=status, message_id=message_id, page=page, page_size=page_size, sort=sort
    )


@router.get("/tasks/{task_id}")
def get_task(task_id: int, user: dict = Depends(require_roles(Role.SECRETARY))):
    return task_service.get_task(task_id, user)


@router.post("/tasks/{task_id}/review")
def review_task(task_id: int, body: TaskReviewIn,
                user: dict = Depends(require_roles(Role.SECRETARY)),
                ip: str = Depends(client_ip), ua: str = Depends(client_ua)):
    """审核部门任务：APPROVED 通过 / REJECTED 驳回（必须填写批注，任务回到 PENDING）。"""
    return task_service.task_review(user, task_id, body.result, body.comment, ip, ua)


@router.post("/messages/{message_id}/archive")
def archive_message(message_id: int, user: dict = Depends(require_roles(Role.SECRETARY)),
                    ip: str = Depends(client_ip), ua: str = Depends(client_ua)):
    """归档已结束留言（COMPLETED / REJECTED → ARCHIVED）。"""
    return message_service.archive(user, message_id, ip, ua)
