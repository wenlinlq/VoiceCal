"""
声历 Agent — FastAPI 应用入口。

启动方式：
    LOG_LEVEL=INFO uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

日志级别：
    LOG_LEVEL=INFO   — 关键节点日志
    LOG_LEVEL=DEBUG  — 包含音频分片等详细日志
"""

import logging
import os

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.agent import router as agent_router
from app.api.websocket import router as ws_router
from app.api.events import router as events_router
from app.api.auth import router as auth_router
from app.api.subscribe import router as subscribe_router
from app.db.database import Base, get_engine
from app.services.push_scheduler import start_push_scheduler, stop_push_scheduler

# 配置全局日志格式
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时自动创建数据库表，启动定时推送调度器。"""
    logger.info("[系统] 应用启动，正在初始化数据库表...")
    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("[系统] 数据库表初始化完成")
    try:
        start_push_scheduler()
    except Exception:
        logger.exception("[系统] 推送调度器启动失败，将继续运行")
    yield
    try:
        stop_push_scheduler()
    except Exception:
        logger.exception("[系统] 推送调度器停止失败")
    logger.info("[系统] 应用关闭")


app = FastAPI(title="声历 Agent", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(agent_router)
app.include_router(ws_router)
app.include_router(events_router)
app.include_router(subscribe_router)

logger.info("[系统] 路由注册完成 health=/api/health auth=/api/auth/wechat-login agent=/api/agent/text ws=/ws/voice events=/api/events subscribe=/api/wechat/subscribe-result")
