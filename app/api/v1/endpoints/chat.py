"""问答接口：普通 + 流式。"""
import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.rag.pipeline.query_pipeline import run_query
from app.schemas.chat import ChatRequest, ChatResponse
from app.services import chat_service, session_service

import asyncio

from app.api.deps import get_current_user
from app.db.models.user import User
from app.api.v1.endpoints.documents import logger

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ChatResponse:
    """非流式问答。"""
    session_id, result = await chat_service.chat(
        db, req.question, req.session_id, req.top_k, user_id=user.id,
    )
    return ChatResponse(
        session_id=session_id,
        question=result.question,
        rewritten_question=result.rewritten_question,
        answer=result.answer,
        sources=result.sources,
    )


@router.post("/stream")
async def chat_stream(req: ChatRequest, db: AsyncSession = Depends(get_db),user: User = Depends(get_current_user)):
    """流式问答，SSE 协议。

    事件类型：
      progress   阶段提示 {stage: "retrieving" | "generating"}
      sources    引用来源 {items: [...]}
      token      LLM 输出片段 {text: "..."}    ← 现在是真·LLM token
      done       结束     {session_id: "..."}
      error      错误     {message: "..."}
    """

    async def event_gen():
        try:
            # ---- 会话准备 ----
            session = await session_service.get_or_create(
                db, req.session_id, user_id=user.id,
            )
            await session_service.auto_title_from_question(db, session, req.question)
            history = await session_service.history_for_condense(db, session.id)
            await session_service.append_message(db, session.id, "user", req.question)

            yield _sse("progress", {"stage": "retrieving"})

            # ---- 多轮问题改写（同步 → 线程池）----
            from app.rag.chains.condense_chain import condense_question
            try:
                rewritten = await asyncio.wait_for(
                    asyncio.to_thread(condense_question, req.question, history),
                    timeout=10.0,
                )
            except asyncio.TimeoutError:
                logger.warning("问题改写超时，使用原问题")
                rewritten = req.question

            # 检索长期记忆
            memory_block = ""
            memory_count = 0
            try:
                from app.memory import long_term
                memory_block, memory_count = await long_term.build_memory_context(
                    db, user.id, rewritten, top_k=3,
                )
                if memory_count > 0:
                    yield _sse("memory", {"count": memory_count})
            except Exception as e:  # noqa: BLE001
                logger.warning("记忆检索失败：%s", e)

            # ---- 真·流式生成 ----
            from app.rag.chains.qa_chain import astream_answer

            sources: list[dict] = []
            answer_parts: list[str] = []

            async for event, data in astream_answer(
                rewritten,
                top_k=req.top_k,
                memory_block=memory_block,
            ):
                if event == "sources":
                    sources = data or []
                    yield _sse("sources", {"items": sources})
                    yield _sse("progress", {"stage": "generating"})
                elif event == "token":
                    answer_parts.append(data)
                    yield _sse("token", {"text": data})
                elif event == "done":
                    break

            # ---- 持久化 ----
            full_answer = "".join(answer_parts)
            await session_service.append_message(
                db, session.id, "assistant", full_answer, sources,
            )

            # 摘要压缩
            try:
                await session_service.maybe_compress(db, session)
            except Exception as e:  # noqa: BLE001
                logger.warning("摘要压缩失败：%s", e)

            # 长期记忆提取
            try:
                from app.services.chat_service import _extract_long_term_memories
                await _extract_long_term_memories(
                    db, user.id, session.id, req.question,
                )
            except Exception as e:  # noqa: BLE001
                logger.warning("长期记忆提取失败：%s", e)

            yield _sse("done", {"session_id": session.id})

        except Exception as e:  # noqa: BLE001
            logger.exception("流式问答失败")
            yield _sse("error", {"message": str(e)})

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"