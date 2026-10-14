"""Agent 状态定义。

LangGraph 的状态是一个 TypedDict，每个节点读写这个状态。
关键：messages 用 add_messages reducer，新消息会被追加而不是替换。
"""
from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """Agent 状态。"""

    # 对话消息列表，用 add_messages 自动追加
    messages: Annotated[list[BaseMessage], add_messages]

    # 当前已迭代次数，用于防止无限循环
    iterations: int