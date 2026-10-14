"""记忆效果验证：先建立记忆，再对比有无记忆的回答。

用法：
    python -m scripts.check_memory_effect
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.logging import setup_logging
from app.db.session import AsyncSessionLocal
from app.memory import long_term
from app.services.auth_service import get_user_by_username


async def main() -> None:
    setup_logging()

    async with AsyncSessionLocal() as db:
        user = await get_user_by_username(db, "admin")
        if not user:
            print("⚠️  没有 admin 用户")
            return

        # 先清空旧记忆，避免干扰
        await long_term.clear_user_memories(db, user.id)

        # 手动写入几条身份类记忆
        await long_term.save_extracted(db, user.id, [
            {"content": "用户是字节跳动的算法工程师，主要做推荐方向",
             "type": "fact", "importance": 0.9},
            {"content": "用户偏好用表格对比的方式来理解技术选型",
             "type": "preference", "importance": 0.8},
            {"content": "用户在做 RAG 知识库项目，技术栈是 FastAPI + LangChain",
             "type": "fact", "importance": 0.9},
        ])

        print("已写入 3 条记忆\n")

        # 测试检索
        queries = [
            "用户喜欢什么回答风格",
            "我应该怎么学习 RAG",
            "推荐系统的常见算法有哪些",
        ]

        for q in queries:
            print(f"\n{'=' * 60}\n查询：{q}\n{'=' * 60}")
            block, count = await long_term.build_memory_context(
                db, user.id, q, top_k=3,
            )
            print(f"命中 {count} 条记忆")
            if block:
                print(block)


if __name__ == "__main__":
    asyncio.run(main())