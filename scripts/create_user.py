"""创建用户命令行工具。

用法：
    python -m scripts.create_user <username> <password> <role>
    role 可选：admin / user
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.logging import setup_logging
from app.db.init_db import init_db
from app.db.session import AsyncSessionLocal
from app.services.auth_service import create_user, get_user_by_username


async def main(username: str, password: str, role: str) -> None:
    setup_logging()
    await init_db()
    async with AsyncSessionLocal() as db:
        if await get_user_by_username(db, username):
            print(f"用户已存在：{username}")
            return
        user = await create_user(db, username, password, role)
        print(f"✅ 已创建用户：{user.username} (role={user.role})")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)
    asyncio.run(main(sys.argv[1], sys.argv[2], sys.argv[3]))