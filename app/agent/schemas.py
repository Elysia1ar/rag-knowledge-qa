"""Agent 结构化输出 Schema。"""
from pydantic import BaseModel, Field


class PlanStep(BaseModel):
    """计划中的单个步骤。"""

    step: int = Field(..., description="步骤序号，从 1 开始")
    description: str = Field(
        ...,
        description="步骤描述，说明这一步要做什么、要查询什么信息",
    )
    tool: str = Field(
        default="search_knowledge",
        description="本步骤要用的工具名，可选 search_knowledge / get_current_time / list_documents",
    )


class Plan(BaseModel):
    """完整的执行计划。"""

    goal: str = Field(..., description="对用户问题的一句话概括")
    steps: list[PlanStep] = Field(
        ...,
        min_length=1,
        max_length=6,
        description="执行步骤列表，最多 6 步",
    )
    reasoning: str = Field(
        default="",
        description="为什么要这样规划（简短说明）",
    )