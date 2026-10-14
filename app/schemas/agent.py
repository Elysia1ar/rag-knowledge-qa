"""Agent 请求/响应。"""
from typing import Literal

from pydantic import BaseModel, Field


from typing import Literal

class AgentChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    session_id: str | None = Field(None, description="不传则创建新会话")
    agent_mode: Literal["react", "plan"] = Field(
        "react",
        description="思考模式：react（边想边做）或 plan（先规划再执行）",
    )

class AgentStepModel(BaseModel):
    """Agent 中间步骤。"""
    type: Literal["action", "observation"]
    name: str | None = None       # action 才有
    args: dict | None = None      # action 才有
    content: str | None = None    # observation 才有


class AgentChatResponse(BaseModel):
    session_id: str
    question: str
    answer: str
    steps: list[AgentStepModel] = []