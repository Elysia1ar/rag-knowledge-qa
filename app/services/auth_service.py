"""用户认证与初始化。"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.security import hash_password, verify_password
from app.db.models.user import User


logger = get_logger(__name__)


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    stmt = select(User).where(User.username == username)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def authenticate(db: AsyncSession, username: str, password: str) -> User | None:
    user = await get_user_by_username(db, username)
    if not user or not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


async def create_user(
    db: AsyncSession,
    username: str,
    password: str,
    role: str = "user",
) -> User:
    user = User(
        username=username,
        password_hash=hash_password(password),
        role=role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def ensure_default_admin(db: AsyncSession) -> None:
    """启动时如果用户表为空，创建默认 admin。"""
    s = get_settings()
    result = await db.execute(select(User).limit(1))
    if result.scalar_one_or_none():
        return

    logger.warning(
        "用户表为空，创建默认管理员：%s / %s（请尽快修改密码）",
        s.default_admin_username, s.default_admin_password,
    )
    await create_user(
        db,
        username=s.default_admin_username,
        password=s.default_admin_password,
        role="admin",
    )