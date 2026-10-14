"""异步数据库会话。"""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings


_settings = get_settings()

engine = create_async_engine(
    _settings.db_url,
    echo=_settings.db_echo,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖注入用的异步 session。"""
    async with AsyncSessionLocal() as session:
        yield session