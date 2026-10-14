"""Agent 业务编排。

职责：
  1. 会话历史注入 —— 把 DB 里的对话历史转成 LangChain 消息
  2. 同步/流式调用 Agent
  3. 会话持久化 —— 只存用户问题 + 最终答案，中间态不入库
"""
import asyncio
from dataclasses import dataclass, field

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.react_agent import get_react_agent
from app.core.logging import get_logger
from app.services import session_service

from app.agent.plan_solve_agent import get_plan_solve_agent

logger = get_logger(__name__)


@dataclass
class AgentStep:
    type: str          # "action" | "observation"
    name: str | None = None
    args: dict | None = None
    content: str | None = None


@dataclass
class AgentResult:
    question: str
    answer: str
    steps: list[AgentStep] = field(default_factory=list)


def _history_to_messages(history: list[dict]) -> list:
    from langchain_core.messages import SystemMessage

    msgs = []
    for h in history:
        if h["role"] == "user":
            msgs.append(HumanMessage(content=h["content"]))
        elif h["role"] == "assistant":
            msgs.append(AIMessage(content=h["content"]))
        elif h["role"] == "system":
            msgs.append(SystemMessage(content=h["content"]))
    return msgs


def _extract_result(messages: list) -> tuple[str, list[AgentStep]]:
    """从完整 messages 列表提取最终答案和中间步骤。"""
    steps: list[AgentStep] = []
    final_answer = ""

    for msg in messages:
        if isinstance(msg, AIMessage):
            tool_calls = getattr(msg, "tool_calls", None) or []
            if tool_calls:
                for tc in tool_calls:
                    steps.append(AgentStep(
                        type="action",
                        name=tc.get("name"),
                        args=tc.get("args"),
                    ))
            elif msg.content:
                # 更新为最新一条有内容的 AIMessage（最终答案）
                final_answer = msg.content

        elif isinstance(msg, ToolMessage):
            steps.append(AgentStep(
                type="observation",
                content=str(msg.content)[:500],
            ))

    return final_answer, steps


async def chat(
    db: AsyncSession,
    question: str,
    session_id: str | None = None,
    user_id: int | None = None,
) -> tuple[str, AgentResult]:
    session = await session_service.get_or_create(db, session_id, user_id=user_id)
    await session_service.auto_title_from_question(db, session, question)
    history = await session_service.history_for_condense(db, session.id)
    await session_service.append_message(db, session.id, "user", question)

    messages = _history_to_messages(history)
    messages.append(HumanMessage(content=question))

    agent = get_react_agent()
    # LangGraph 的 invoke 是同步阻塞，扔线程池
    result = await asyncio.to_thread(
        agent.invoke,
        {"messages": messages, "iterations": 0},
    )

    answer, steps = _extract_result(result["messages"])

    await session_service.append_message(
        db, session.id, "assistant", answer, sources=[],
    )

    return session.id, AgentResult(question=question, answer=answer, steps=steps)


async def chat_stream(
    db: AsyncSession,
    question: str,
    session_id: str | None = None,
    agent_mode: str = "react",          # ← 新增: "react" | "plan"
    user_id: int | None = None
):
    
    """流式版本：用 astream_events 转发 Agent 的每一步。

    yield 结构：(event: str, data: dict)
      progress    {"stage": "thinking"}
      action      {"name": str, "args": dict}
      observation {"preview": str}
      token       {"text": str}
      done        {"session_id": str}
      error       {"message": str}
    """
    
    # ---- Plan-and-Solve 分支：完全独立，内部自己处理会话 ----
    if agent_mode == "plan":
        async for evt in stream_plan_solve(db, question, session_id, user_id=user_id):
            yield evt
        return
    
    session = await session_service.get_or_create(db, session_id, user_id=user_id)
    history = await session_service.history_for_condense(db, session.id)
    await session_service.append_message(db, session.id, "user", question)

    messages = _history_to_messages(history)
    messages.append(HumanMessage(content=question))

    agent = get_react_agent()

    yield ("progress", {"stage": "thinking"})

    answer_parts: list[str] = []

    try:
        async for event in agent.astream_events(
            {"messages": messages, "iterations": 0},
            version="v2",
        ):
            kind = event.get("event")

            # ---- 工具开始：推 action ----
            if kind == "on_tool_start":
                name = event.get("name", "")
                args = event.get("data", {}).get("input", {}) or {}
                logger.info("[stream] action | %s | %s", name, args)
                yield ("action", {"name": name, "args": args})

            # ---- 工具结束：推 observation ----
            elif kind == "on_tool_end":
                output = str(event.get("data", {}).get("output", ""))
                preview = output[:500]
                logger.info("[stream] observation | %d chars", len(output))
                yield ("observation", {"preview": preview})

            # ---- LLM 流式 token ----
            elif kind == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                if chunk is None:
                    continue

                text = getattr(chunk, "content", "") or ""
                tcc = getattr(chunk, "tool_call_chunks", None) or []

                # 关键判断：决策阶段的 chunk = 有 tool_call_chunks 且 content 为空
                # 答案阶段：content 有实际文本，忽略 tcc（可能是空列表占位）
                if tcc and not text:
                    continue

                if text:
                    answer_parts.append(text)
                    yield ("token", {"text": text})

    except Exception as e:  # noqa: BLE001
        logger.exception("Agent 流式执行失败")
        yield ("error", {"message": str(e)})

    # ---- 持久化最终答案 ----
    full_answer = "".join(answer_parts)
    await session_service.append_message(
        db, session.id, "assistant", full_answer, sources=[],
    )

    # 触发摘要压缩
    try:
        await session_service.maybe_compress(db, session)
    except Exception as e:
        logger.warning("摘要压缩失败：%s", e)

    # 触发长期记忆提取（需要 user_id 参数）
    if user_id is not None:
        try:
            from app.services.chat_service import _extract_long_term_memories
            await _extract_long_term_memories(
                db, user_id, session.id, question,
            )
        except Exception as e:
            logger.warning("长期记忆提取失败：%s", e)

    yield ("done", {"session_id": session.id})

async def stream_plan_solve(
    db: AsyncSession,
    question: str,
    session_id: str | None = None,
):
    """Plan-and-Solve 模式的流式执行。

    事件序列：
      progress(planning) → plan → progress(executing) → step × N → progress(solving) → token × N → done
    """
    session = await session_service.get_or_create(db, session_id)
    history = await session_service.history_for_condense(db, session.id)
    await session_service.append_message(db, session.id, "user", question)

    agent = get_plan_solve_agent()

    yield ("progress", {"stage": "planning"})

    answer_parts: list[str] = []
    plan_sent = False
    executor_step_sent = 0

    try:
        async for event in agent.astream_events(
            {"question": question, "current_step": 0, "step_results": []},
            version="v2",
        ):
            kind = event.get("event")
            name = event.get("name")

            # Plan 生成完成
            if kind == "on_chain_end" and name == "planner":
                output = event.get("data", {}).get("output", {})
                plan = output.get("plan")
                if plan and not plan_sent:
                    yield ("plan", {
                        "goal": plan.goal,
                        "reasoning": plan.reasoning,
                        "steps": [
                            {"step": s.step, "description": s.description, "tool": s.tool}
                            for s in plan.steps
                        ],
                    })
                    yield ("progress", {"stage": "executing"})
                    plan_sent = True

            # Executor 每执行完一步
            elif kind == "on_chain_end" and name == "executor":
                output = event.get("data", {}).get("output", {})
                results = output.get("step_results", [])
                if len(results) > executor_step_sent:
                    r = results[-1]
                    yield ("step_done", {
                        "step": r["step"],
                        "description": r["description"],
                        "preview": r["result"][:500],
                    })
                    executor_step_sent = len(results)

            # Solver 开始
            elif kind == "on_chain_start" and name == "solver":
                yield ("progress", {"stage": "solving"})

            # Solver 的流式 token
            elif kind == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                if chunk is None:
                    continue
                text = getattr(chunk, "content", "") or ""
                if text:
                    answer_parts.append(text)
                    yield ("token", {"text": text})

    except Exception as e:  # noqa: BLE001
        logger.exception("Plan-and-Solve 执行失败")
        yield ("error", {"message": str(e)})

    full_answer = "".join(answer_parts)
    await session_service.append_message(
        db, session.id, "assistant", full_answer, sources=[],
    )
    yield ("done", {"session_id": session.id})