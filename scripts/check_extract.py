"""自动记忆提取验证。

用法：
    python -m scripts.check_extract
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.logging import setup_logging
from app.db.session import AsyncSessionLocal
from app.memory import long_term
from app.memory.extractor import extract_memories
from app.services import session_service
from app.services.auth_service import get_user_by_username


# 模拟一段对话：混入 "值得记住" 和 "不该记住" 的内容
FAKE_DIALOG = [
    ("user", "你好，我在做一个 RAG 知识库项目，技术栈是 FastAPI + LangChain"),
    ("assistant", "很不错的项目，RAG 是当前很热的方向"),
    ("user", "我平时喜欢用表格对比的方式来理解技术选型"),
    ("assistant", "好的，我会尽量用表格"),
    ("user", "对了，RAG 和 fine-tuning 有什么区别？"),
    ("assistant", "RAG 通过检索增强，fine-tuning 通过调整模型参数..."),
    ("user", "我目前在字节跳动做算法工程师，主要是推荐方向"),
    ("assistant", "了解"),
]


async def main() -> None:
    setup_logging()

    async with AsyncSessionLocal() as db:
        user = await get_user_by_username(db, "admin")
        if not user:
            print("⚠️  没有 admin 用户")
            return

        print(f"用户: {user.username} (id={user.id})\n")

        # 清空旧记忆
        n = await long_term.clear_user_memories(db, user.id)
        print(f"清空旧记忆 {n} 条\n")

        # 构造真实 Message 对象（不落库，直接构造）
        from app.db.models.chat import Message

        messages = [
            Message(session_id="test", role=r, content=c, sources_json="[]")
            for r, c in FAKE_DIALOG
        ]

        # 1. 提取
        print("=" * 60)
        print("1. 提取候选记忆")
        print("=" * 60)
        items = await extract_memories(messages)
        for i, item in enumerate(items, 1):
            print(f"  [{i}] type={item['type']:12s} imp={item['importance']:.2f}")
            print(f"      {item['content']}")

        # 2. 保存
        print(f"\n{'=' * 60}")
        print("2. 保存到记忆库")
        print("=" * 60)
        n = await long_term.save_extracted(db, user.id, items)
        print(f"  保存 {n} 条")

        # 3. 列出
        print(f"\n{'=' * 60}")
        print("3. 列出用户所有记忆")
        print("=" * 60)
        mems = await long_term.list_memories(db, user.id)
        for m in mems:
            print(f"  [{m.id}] {m.memory_type:12s} imp={m.importance:.2f} | {m.content[:50]}")

        # 4. 检索（含低分过滤）
        print(f"\n{'=' * 60}")
        print("4. 检索：'用户喜欢什么回答方式'（含重要性过滤）")
        print("=" * 60)
        results = await long_term.search_memories(
            db, user.id, "用户喜欢什么回答方式", top_k=5,
        )
        for m in results:
            print(f"  [{m.id}] imp={m.importance:.2f} | {m.content}")


if __name__ == "__main__":
    asyncio.run(main())