"""记忆固化验证。

用法：
    python -m scripts.check_consolidate
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.logging import setup_logging
from app.db.session import AsyncSessionLocal
from app.memory import long_term
from app.memory.consolidate import consolidate_from_summary
from app.services.auth_service import get_user_by_username


# 模拟一个累积摘要（包含多个会话的归纳）
FAKE_SUMMARY = """
用户在过去多次对话中持续关注 RAG 系统的构建与优化。具体表现为：
第一，反复询问检索质量相关问题（混合检索、BM25、RRF 融合）；
第二，多轮对话都涉及重排序策略（Bi-Encoder 与 Cross-Encoder 的对比、Reranker 模型选型）；
第三，明确表示在做生产级 RAG 项目，技术栈是 FastAPI + LangChain + Chroma；
第四，多次提到要量化评估效果（RAGAS 指标、消融实验设计）；
第五，偏好用表格对比理解技术选型，且经常追问"为什么"背后的原理。
"""


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

        # 先写入几条"逐轮提取"的记忆（模拟 C3.4 已经跑过）
        await long_term.save_extracted(db, user.id, [
            {"content": "用户在做 RAG 项目，技术栈 FastAPI + LangChain",
             "type": "fact", "importance": 0.9},
            {"content": "用户偏好用表格对比理解技术选型",
             "type": "preference", "importance": 0.8},
        ])
        print("已写入 2 条逐轮提取记忆\n")

        # 1. 固化
        print("=" * 60)
        print("1. 从摘要固化跨轮归纳记忆")
        print("=" * 60)
        n = await consolidate_from_summary(
            db, user.id, FAKE_SUMMARY, session_id="test_session",
        )
        print(f"\n固化 {n} 条\n")

        # 2. 列出所有记忆
        print("=" * 60)
        print("2. 用户全部记忆")
        print("=" * 60)
        mems = await long_term.list_memories(db, user.id)
        for m in mems:
            print(
                f"  [{m.id}] {m.memory_type:12s} imp={m.importance:.2f} | "
                f"{m.content[:60]}"
            )

        # 3. 再去重一次（应该全部被跳过）
        print(f"\n{'=' * 60}")
        print("3. 重复固化（应全部去重）")
        print("=" * 60)
        n2 = await consolidate_from_summary(
            db, user.id, FAKE_SUMMARY, session_id="test_session",
        )
        print(f"固化 {n2} 条（应接近 0）")


if __name__ == "__main__":
    asyncio.run(main())