"""Agent 接口。"""
import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.agent import AgentChatRequest, AgentChatResponse, AgentStepModel
from app.services import agent_service

from app.api.deps import get_current_user
from app.db.models.user import User

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/chat", response_model=AgentChatResponse)
async def agent_chat(
    req: AgentChatRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AgentChatResponse:
    """非流式 Agent 问答。"""
    session_id, result = await agent_service.chat(
        db, req.question, req.session_id, user_id=user.id,
    )
    return AgentChatResponse(
        session_id=session_id,
        question=result.question,
        answer=result.answer,
        steps=[
            AgentStepModel(
                type=s.type, name=s.name, args=s.args, content=s.content,
            )
            for s in result.steps
        ],
    )


@router.post("/chat/stream")
async def agent_chat_stream(
    req: AgentChatRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """流式 Agent 问答（SSE）。

    事件类型：
      progress    阶段提示 {stage: "thinking"}
      action      Agent 决定调用工具 {name, args}
      observation 工具返回结果 {preview}
      token       最终答案 token {text}
      done        结束 {session_id}
      error       错误 {message}
    """
    async def event_gen():
        try:
            async for event, data in agent_service.chat_stream(
                db, req.question, req.session_id, req.agent_mode, user_id=user.id,
            ):
                yield _sse(event, data)
        except Exception as e:  # noqa: BLE001
            yield _sse("error", {"message": str(e)})

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"