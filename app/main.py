"""FastAPI 应用入口。"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.db.init_db import init_db


logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("启动中……")
    await init_db()

    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        # 1) 创建默认 admin（表为空时）
        try:
            from app.services.auth_service import ensure_default_admin
            await ensure_default_admin(db)
        except Exception as e:
            logger.warning("初始化 admin 失败：%s", e)

        # 2) 同步磁盘文档到 DB
        try:
            from app.services.document_service import sync_from_disk
            await sync_from_disk(db)
        except Exception as e:
            logger.warning("启动同步失败：%s", e)

    yield
    logger.info("关闭")


def create_app() -> FastAPI:
    s = get_settings()
    app = FastAPI(
        title="RAG Knowledge QA",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=s.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router)
    return app


app = create_app()