"""路由聚合。"""
from fastapi import APIRouter

from app.api import admin, anonymous, attachment, auth, department, principal, secretary

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(anonymous.router)
api_router.include_router(principal.router)
api_router.include_router(secretary.router)
api_router.include_router(department.router)
api_router.include_router(admin.router)
api_router.include_router(attachment.router)
