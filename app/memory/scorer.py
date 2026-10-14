"""用 LLM 给记忆内容打分。

打分维度（参照 Generative Agents + Hello-Agents）：
  1. 用户身份、长期目标     → 0.9~1.0
  2. 具体技术选择、项目信息 → 0.6~0.8
  3. 一般知识问答           → 0.3~0.5
  4. 寒暄、闲聊、无关内容   → 0.0~0.2
"""
import re

from langchain_core.messages import HumanMessage

from app.core.logging import get_logger
from app.rag.llm import get_llm


logger = get_logger(__name__)


_SCORE_PROMPT = """评估以下信息对构建用户长期画像的价值，输出 0~1 的分数。

评分标准：
- 0.9~1.0：用户身份、职业、核心偏好、长期目标
- 0.6~0.8：具体的技术选择、项目信息、关键结论、明确偏好
- 0.3~0.5：一般性知识问答、临时性提问
- 0.0~0.2：寒暄、闲聊、与用户无关的内容

信息：
{content}

只输出一个数字（0~1 之间，可以是小数），不要任何其他内容。"""


async def score_importance(content: str) -> float:
    """给一段内容打 0~1 的重要性分数。

    解析失败时返回 0.5（中性）。
    """
    content = content.strip()
    if not content:
        return 0.0

    try:
        llm = get_llm()
        result = await llm.ainvoke([
            HumanMessage(content=_SCORE_PROMPT.format(content=content))
        ])
        text = result.content.strip()
    except Exception as e:  # noqa: BLE001
        logger.warning("打分失败：%s", e)
        return 0.5

    # 从返回文本里抠出第一个数字
    m = re.search(r"(\d+(?:\.\d+)?)", text)
    if not m:
        logger.warning("打分返回无法解析：%r", text[:50])
        return 0.5

    try:
        score = float(m.group(1))
    except ValueError:
        return 0.5

    return max(0.0, min(1.0, score))