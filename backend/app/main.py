"""FastAPI 主应用：CORS、防刷中间件、路由、连接池生命周期、健康检查。"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core import ratelimit
from app.core.config import get_settings
from app.db import database as db


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    os.makedirs(s.upload_dir, exist_ok=True)
    db.init_pool()
    yield
    db.close_pool()


app = FastAPI(
    title="医院匿名留言板系统",
    description="匿名提交、秘书审核、院长批示、部门处理、匿名查询评价的全流程留言板",
    version="1.0.0",
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_and_ratelimit(request, call_next):
    blocked = ratelimit.check_and_limit(request)
    if blocked is not None:
        return blocked
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


app.include_router(api_router)


@app.get("/api/health")
def health():
    try:
        db.scalar("SELECT 1 AS ok")
        return {"status": "ok", "db": "up"}
    except Exception as e:  # pragma: no cover
        return JSONResponse(status_code=503, content={"status": "error", "db": "down", "detail": str(e)})
