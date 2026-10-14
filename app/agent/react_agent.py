"""基于 LangGraph 的 ReAct Agent。

流程：
    START → agent → (有 tool_calls?) → tools → agent → ... → END

节点说明：
  - agent: 调用 LLM，让它决定下一步
  - tools: 执行 LLM 请求的工具调用
"""
from typing import Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph

from app.agent.prompts import AGENT_SYSTEM_PROMPT
from app.agent.state import AgentState
from app.agent.tools import ALL_TOOLS
from app.core.config import get_settings
from app.core.logging import get_logger


logger = get_logger(__name__)


def _build_llm() -> ChatOpenAI:
    """构建 Agent 用的 LLM，绑定工具。

    注意：streaming=True 是必须的——否则 astream_events 拿不到
    on_chat_model_stream 事件，token 无法流式推送。
    """
    s = get_settings()
    llm = ChatOpenAI(
        model=s.llm_model,
        api_key=s.llm_api_key,
        base_url=s.llm_base_url,
        temperature=s.agent_temperature,
        streaming=True,                # ← 改为 True
    )
    return llm.bind_tools(ALL_TOOLS)


# 工具名 → 工具函数 的映射，用于 tool_node 执行
_TOOL_MAP = {t.name: t for t in ALL_TOOLS}


def build_react_agent():
    """构建并编译 ReAct Agent 图。"""

    llm_with_tools = _build_llm()
    s = get_settings()

    # ---------- 节点 1：agent ----------
    def agent_node(state: AgentState) -> dict:
        """调用 LLM，让它决定下一步（调工具 or 给最终回答）。"""
        iterations = state.get("iterations", 0)

        # 超过迭代上限，强制结束
        if iterations >= s.agent_max_iterations:
            logger.warning("Agent 达到最大迭代次数 %d，强制结束", iterations)
            return {
                "messages": [
                    AIMessage(content="（已达到最大工具调用次数，基于现有信息给出回答）")
                ],
                "iterations": iterations,
            }

        # 首次调用，注入系统提示
        messages = state["messages"]
        if not any(isinstance(m, SystemMessage) for m in messages):
            messages = [SystemMessage(content=AGENT_SYSTEM_PROMPT)] + messages

        response = llm_with_tools.invoke(messages)

        tool_calls = getattr(response, "tool_calls", None) or []
        if tool_calls:
            logger.info(
                "Agent 第 %d 轮 | 决定调用 %s",
                iterations + 1,
                [tc["name"] for tc in tool_calls],
            )
        else:
            logger.info("Agent 第 %d 轮 | 给出最终回答", iterations + 1)

        return {
            "messages": [response],
            "iterations": iterations + 1,
        }

    # ---------- 节点 2：tools ----------
    def tools_node(state: AgentState) -> dict:
        """执行 LLM 请求的所有工具调用，把结果作为 ToolMessage 返回。"""
        last_msg = state["messages"][-1]
        tool_calls = getattr(last_msg, "tool_calls", None) or []

        tool_messages: list[ToolMessage] = []
        for tc in tool_calls:
            name = tc["name"]
            args = tc["args"]
            call_id = tc["id"]

            tool_fn = _TOOL_MAP.get(name)
            if not tool_fn:
                result = f"未知工具：{name}"
            else:
                try:
                    result = tool_fn.invoke(args)
                except Exception as e:
                    logger.exception("工具执行失败: %s", name)
                    result = f"工具执行失败：{e}"

            tool_messages.append(
                ToolMessage(content=str(result), tool_call_id=call_id)
            )

        return {"messages": tool_messages}

    # ---------- 条件边：判断是否需要调工具 ----------
    def should_continue(state: AgentState) -> Literal["tools", "end"]:
        """检查 LLM 最新回复是否包含 tool_calls。"""
        last_msg = state["messages"][-1]
        if getattr(last_msg, "tool_calls", None):
            return "tools"
        return "end"

    # ---------- 构建图 ----------
    graph = StateGraph(AgentState)

    graph.add_node("agent", agent_node)
    graph.add_node("tools", tools_node)

    graph.add_edge(START, "agent")
    graph.add_conditional_edges(
        "agent",
        should_continue,
        {"tools": "tools", "end": END},
    )
    graph.add_edge("tools", "agent")     # 工具执行完回到 agent 继续思考

    return graph.compile()


# 单例：Agent 图构建成本高，复用
_agent = None


def get_react_agent():
    """获取 ReAct Agent 单例。"""
    global _agent
    if _agent is None:
        _agent = build_react_agent()
    return _agent