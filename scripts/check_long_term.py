"""长期记忆基础验证：保存 / 检索 / 删除。

用法：
    python -m scripts.check_long_term
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.logging import setup_logging
from app.db.session import AsyncSessionLocal
from app.memory import long_term
from app.services.auth_service import get_user_by_username


SAMPLE_MEMORIES = [
    ("用户从事机器人开发，主攻 ROS 和运动控制", "fact", 0.9),
    ("用户偏好用表格对比的回答形式", "preference", 0.8),
    ("用户正在做一个 RAG 知识库项目，技术栈是 FastAPI + LangChain", "fact", 0.9),
    ("用户倾向使用 DeepSeek 作为 LLM，因为性价比高", "preference", 0.7),
    ("用户之前讨论过 PID 控制器的位置式和增量式形式", "conclusion", 0.6),
    ("用户问我今天天气怎么样（这个不应该被记住）", "event", 0.1),
]


async def main() -> None:
    setup_logging()

    async with AsyncSessionLocal() as db:
        # 用 admin 用户测试
        user = await get_user_by_username(db, "admin")
        if not user:
            print("⚠️  没有 admin 用户，先创建一个")
            return

        print(f"用户: {user.username} (id={user.id})\n")

        # 1. 保存
        print("=" * 60)
        print("1. 保存 6 条记忆")
        print("=" * 60)
        for content, mtype, imp in SAMPLE_MEMORIES:
            m = await long_term.save_memory(
                db, user.id, content,
                memory_type=mtype, importance=imp,
            )
            print(f"  [id={m.id}] {mtype:12s} imp={imp:.1f} | {content[:40]}")

        # 2. 列出全部
        print(f"\n{'=' * 60}")
        print("2. 列出所有记忆（按重要性倒序）")
        print("=" * 60)
        all_mems = await long_term.list_memories(db, user.id)
        for m in all_mems:
            print(f"  [{m.id}] {m.memory_type:12s} imp={m.importance:.1f} | {m.content[:40]}")

        # 3. 检索
        print(f"\n{'=' * 60}")
        print("3. 检索：'我最近在做什么项目'")
        print("=" * 60)
        results = await long_term.search_memories(
            db, user.id, "我最近在做什么项目", top_k=3,
        )
        for m in results:
            print(f"  [{m.id}] {m.content[:60]}")
            print(f"       access_count={m.access_count}")

        # 4. 检索（应该只命中相关记忆）
        print(f"\n{'=' * 60}")
        print("4. 检索：'用户喜欢什么回答风格'")
        print("=" * 60)
        results = await long_term.search_memories(
            db, user.id, "用户喜欢什么回答风格", top_k=3,
        )
        for m in results:
            print(f"  [{m.id}] {m.content[:60]}")

        # 5. 删除一条
        print(f"\n{'=' * 60}")
        print("5. 删除最后一条记忆")
        print("=" * 60)
        last = all_mems[-1]
        ok = await long_term.delete_memory_by_id(db, last.id, user.id)
        print(f"  删除 [id={last.id}]: {ok}")

        # 6. 清理（可选，注释掉保留数据）
        # n = await long_term.clear_user_memories(db, user.id)
        # print(f"\n清理了 {n} 条记忆")


if __name__ == "__main__":
    asyncio.run(main())