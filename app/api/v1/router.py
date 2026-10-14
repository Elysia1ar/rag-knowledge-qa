"""v1 总路由。"""
from fastapi import APIRouter

from app.api.v1.endpoints import (
    agent,
    auth,
    chat,
    documents,
    health,
    index,
    memories,
    sessions,
    stats,
)


api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(chat.router)
api_router.include_router(agent.router)      # ← 新增
api_router.include_router(documents.router)
api_router.include_router(index.router)
api_router.include_router(stats.router)
api_router.include_router(sessions.router)
api_router.include_router(health.router)
api_router.include_router(memories.router)