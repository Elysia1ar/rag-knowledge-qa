"""Plan-and-Solve Agent。

三阶段：
  1. Planner: 把问题拆解为结构化计划
  2. Executor: 逐步执行计划中的每一步
  3. Solver: 汇总所有资料，生成最终答案
"""
from typing import Literal, TypedDict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph

from app.agent.planner_prompt import (
    PLANNER_SYSTEM,
    SOLVER_SYSTEM,
    SOLVER_USER_TEMPLATE,
)
from app.agent.schemas import Plan
from app.agent.tools import ALL_TOOLS
from app.core.config import get_settings
from app.core.logging import get_logger


logger = get_logger(__name__)


_TOOL_MAP = {t.name: t for t in ALL_TOOLS}

# ---- 状态定义：用 TypedDict，LangGraph 才会正确 merge ----
class PlanSolveState(TypedDict, total=False):
    """Plan-and-Solve 的状态。

    total=False 让所有字段可选，允许初始状态只传 question。
    节点返回的 dict 只更新对应字段，其余字段保留。
    """
    question: str
    plan: Plan
    current_step: int
    step_results: list[dict]
    final_answer: str

def _base_llm(streaming: bool = False, temperature: float | None = None):
    s = get_settings()
    return ChatOpenAI(
        model=s.llm_model,
        api_key=s.llm_api_key,
        base_url=s.llm_base_url,
        temperature=temperature if temperature is not None else 0.0,
        streaming=streaming,
        # 关键：抑制 tool_choice，解决 DeepSeek 思考模式 400 错误
        disabled_params={"tool_choice": None},
    )


def build_plan_solve_agent():
    """构建 Plan-and-Solve Agent 图。"""

    # ---------- 阶段 1：Planner ----------
    # DeepSeek 不支持 json_schema 格式的 response_format，
    # 改用 function_calling 模式——DeepSeek 支持 tool calling
    planner_llm = _base_llm().with_structured_output(
        Plan,
        method="function_calling",
    )

    def planner_node(state: dict) -> dict:
        question = state["question"]
        logger.info("[plan] 开始规划 | %s", question[:60])

        plan: Plan = planner_llm.invoke([
            SystemMessage(content=PLANNER_SYSTEM),
            HumanMessage(content=question),
        ])

        logger.info(
            "[plan] 规划完成 | goal=%s | %d 步",
            plan.goal, len(plan.steps),
        )
        for s in plan.steps:
            logger.info("  step %d: %s | tool=%s", s.step, s.description, s.tool)

        return {
            "plan": plan,
            "current_step": 0,
            "step_results": [],
        }

    # ---------- 阶段 2：Executor ----------
    def executor_node(state: dict) -> dict:
        plan: Plan = state["plan"]
        idx: int = state["current_step"]
        step = plan.steps[idx]

        logger.info(
            "[exec] 执行 step %d/%d | %s",
            idx + 1, len(plan.steps), step.description,
        )

        tool_fn = _TOOL_MAP.get(step.tool)
        if not tool_fn:
            result = f"[未知工具 {step.tool}]"
        else:
            try:
                # 从 step 描述里提取工具参数
                # 简化策略：search_knowledge 用 description 作为 query
                if step.tool == "search_knowledge":
                    args = {"query": step.description}
                else:
                    args = {}
                result = tool_fn.invoke(args)
            except Exception as e:  # noqa: BLE001
                logger.exception("[exec] step %d 执行失败", idx + 1)
                result = f"[执行失败：{e}]"

        new_results = state["step_results"] + [{
            "step": step.step,
            "description": step.description,
            "tool": step.tool,
            "result": str(result),
        }]

        return {
            "current_step": idx + 1,
            "step_results": new_results,
        }

    def should_continue_executor(state: dict) -> Literal["executor", "solver"]:
        plan: Plan = state["plan"]
        if state["current_step"] < len(plan.steps):
            return "executor"
        return "solver"

    # ---------- 阶段 3：Solver ----------
    solver_llm = _base_llm(streaming=True, temperature=0.1)

    def solver_node(state: dict) -> dict:
        question = state["question"]
        results = state["step_results"]

        # 组装资料
        materials_parts = []
        for r in results:
            materials_parts.append(
                f"【步骤 {r['step']}】{r['description']}\n{r['result']}"
            )
        materials = "\n\n---\n\n".join(materials_parts)

        logger.info("[solve] 汇总 %d 步资料，生成最终回答", len(results))

        response = solver_llm.invoke([
            SystemMessage(content=SOLVER_SYSTEM),
            HumanMessage(content=SOLVER_USER_TEMPLATE.format(
                question=question,
                materials=materials,
            )),
        ])

        return {"final_answer": response.content}

    # ---------- 构建图 ----------
    graph = StateGraph(PlanSolveState)

    graph.add_node("planner", planner_node)
    graph.add_node("executor", executor_node)
    graph.add_node("solver", solver_node)

    graph.add_edge(START, "planner")
    graph.add_edge("planner", "executor")
    graph.add_conditional_edges(
        "executor",
        should_continue_executor,
        {"executor": "executor", "solver": "solver"},
    )
    graph.add_edge("solver", END)

    return graph.compile()


_agent = None


def get_plan_solve_agent():
    """获取 Plan-and-Solve Agent 单例。"""
    global _agent
    if _agent is None:
        _agent = build_plan_solve_agent()
    return _agent