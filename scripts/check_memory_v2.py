"""真实链路短期记忆验证：走 chat_service。"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.logging import setup_logging
from app.db.session import AsyncSessionLocal
from app.services import chat_service, session_service


QUESTIONS = [
    "RAG 的典型管线包括哪些步骤？",
    "为什么要用混合检索？",
    "Cross-Encoder 和 Bi-Encoder 有什么区别？",
    "bge-reranker 有哪些模型？",
    "RAGAS 评估有哪些指标？",
    "什么是 RRF 融合？",
    "分块策略如何选择？",
    "Chroma 和 Milvus 怎么选？",
    "如何在 prompt 里防止幻觉？",
    "如何量化 RAG 效果？",
]


async def main() -> None:
    setup_logging()

    async with AsyncSessionLocal() as db:
        session_id = None
        for i, q in enumerate(QUESTIONS, 1):
            sid, result = await chat_service.chat(
                db, q, session_id=session_id, user_id=1,
            )
            session_id = sid
            print(f"[{i}] {q} → {result.answer[:40]}...")

        # 检查最终状态
        session = await session_service.get_session(db, session_id)
        print(f"\n{'=' * 60}")
        print(f"会话 ID         : {session.id[:16]}")
        print(f"消息总数        : {(await session_service.list_messages(db, session.id)).__len__()}")
        print(f"已摘要条数      : {session.summary_message_count}")
        print(f"摘要长度        : {len(session.summary or '')}")

        print(f"\n摘要预览：\n{(session.summary or '')[:300]}...")

        # 清理
        await session_service.delete_session(db, session.id, user_id=1)
        print(f"\n已清理")


if __name__ == "__main__":
    asyncio.run(main())