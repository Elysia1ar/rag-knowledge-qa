"""初始化数据库：创建所有表。"""
from app.core.logging import get_logger
from app.db.base import Base
from app.db.session import engine
import app.db.models  # noqa: F401  确保模型注册


logger = get_logger(__name__)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("数据库表已就绪")