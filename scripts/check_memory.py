"""短期记忆验证：模拟长对话，观察摘要压缩。

用法：
    python -m scripts.check_memory
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.logging import setup_logging
from app.db.session import AsyncSessionLocal
from app.services import session_service


FAKE_QUESTIONS = [
    "RAG 是什么？",
    "Chroma 和 Milvus 有什么区别？",
    "Bi-Encoder 和 Cross-Encoder 有什么不同？",
    "bge-small 和 bge-large 该怎么选？",
    "混合检索为什么比纯向量好？",
    "RRF 融合的原理是什么？",
    "Cross-Encoder 为什么不用于大规模召回？",
    "embedding 模型的向量维度是多少？",
    "RAGAS 有哪四个评估指标？",
    "消融实验应该怎么设计？",
]


async def main() -> None:
    setup_logging()

    async with AsyncSessionLocal() as db:
        # 创建新会话
        session = await session_service.create_session(db, user_id=1, title="记忆测试")
        print(f"会话 ID: {session.id}\n")

        # 模拟 10 轮问答（每轮 user + assistant，共 20 条消息）
        for i, q in enumerate(FAKE_QUESTIONS, 1):
            await session_service.append_message(db, session.id, "user", q)
            fake_answer = f"这是第 {i} 个问题的模拟回答。" * 10
            await session_service.append_message(
                db, session.id, "assistant", fake_answer,
            )

            # 每轮触发一次压缩
            await db.refresh(session)
            compressed = await session_service.maybe_compress(db, session)
            if compressed:
                print(f"[第 {i} 轮] 触发压缩")

        # 最终状态
        await db.refresh(session)
        print(f"\n{'=' * 60}")
        print(f"总消息数           : {len(await session_service.list_messages(db, session.id))}")
        print(f"summary_message_count: {session.summary_message_count}")
        print(f"summary 长度       : {len(session.summary or '')} 字")
        print(f"\n摘要内容：\n{session.summary}")

        # 验证 history_for_condense
        history = await session_service.history_for_condense(db, session.id)
        print(f"\n{'=' * 60}")
        print(f"history_for_condense 返回 {len(history)} 条：")
        for i, h in enumerate(history, 1):
            content = h["content"][:50].replace("\n", " ")
            print(f"  [{i}] role={h['role']:10s} | {content}...")

        # 清理
        await session_service.delete_session(db, session.id, user_id=1)
        print(f"\n已清理测试会话")


if __name__ == "__main__":
    asyncio.run(main())