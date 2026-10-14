"""记忆固化：从会话摘要中提取跨轮归纳记忆。

与 extractor 的区别：
  extractor：从最近消息提取具体事实
  consolidate：从累积摘要提炼归纳性认知
"""
import json
import re

from langchain_core.messages import HumanMessage
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.memory import long_term
from app.rag.llm import get_llm


logger = get_logger(__name__)


_CONSOLIDATE_PROMPT = """以下是用户与助手的对话摘要。请从中提炼**跨轮归纳性**的长期认知。

只提炼以下类型的信息：
1. 用户长期关注的技术领域或问题域
2. 用户持续表现出的偏好（例如反复要求某种格式、某种深度）
3. 用户正在推进的项目的整体方向
4. 用户在对话中体现出的思维模式或关注点

**不要提炼**：
- 单次问答的具体内容
- 已在具体对话中明确说过的细节
- 通用的技术知识

输出 JSON 数组，每条一行：
{{"content": "...", "type": "fact|preference|conclusion", "importance": 0.7}}

最多输出 3 条。如果没有值得固化的归纳，输出 []。

对话摘要：
{summary}

只输出 JSON 数组："""


def _parse_items(raw: str) -> list[dict]:
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass

    m = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", raw, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass

    start, end = raw.find("["), raw.rfind("]")
    if start != -1 and end > start:
        try:
            return json.loads(raw[start:end + 1])
        except json.JSONDecodeError:
            pass
    return []


async def _is_duplicate(
    db: AsyncSession,
    user_id: int,
    content: str,
    threshold: float = 0.92,
) -> bool:
    """检查是否已有相似度极高的记忆。"""
    from app.rag.vectorstore import get_memory_store

    try:
        vs = get_memory_store()
        hits = vs.similarity_search_with_score(
            content, k=3, filter={"user_id": user_id},
        )
    except Exception:
        return False

    for _doc, dist in hits:
        sim = 1.0 - float(dist) / 2.0
        if sim >= threshold:
            return True
    return False


async def consolidate_from_summary(
    db: AsyncSession,
    user_id: int,
    summary: str,
    *,
    session_id: str | None = None,
) -> int:
    """从摘要中提取归纳记忆并保存。

    Returns:
        成功保存的记忆条数。
    """
    if not summary or len(summary) < 50:
        return 0

    s = get_settings()
    if not s.memory_extract_enabled or not s.memory_consolidate_enabled:
        return 0

    try:
        llm = get_llm()
        result = await llm.ainvoke([
            HumanMessage(content=_CONSOLIDATE_PROMPT.format(summary=summary))
        ])
        items = _parse_items(result.content.strip())
    except Exception as e:  # noqa: BLE001
        logger.warning("固化提取失败：%s", e)
        return 0

    if not items:
        logger.debug("固化：无归纳性记忆")
        return 0

    saved = 0
    for item in items:
        content = (item.get("content") or "").strip()
        if not content:
            continue

        try:
            imp = float(item.get("importance", 0.7))
        except (ValueError, TypeError):
            imp = 0.7

        if imp < s.memory_min_importance:
            continue

        # 去重检查
        if await _is_duplicate(db, user_id, content):
            logger.debug("固化：跳过重复 %s", content[:40])
            continue

        memory_type = item.get("type", "conclusion")
        if memory_type not in ("fact", "preference", "conclusion"):
            memory_type = "conclusion"

        await long_term.save_memory(
            db, user_id,
            content=content,
            memory_type=memory_type,
            importance=imp,
            source_session_id=session_id,
        )
        saved += 1
        logger.info("固化保存 | imp=%.2f | %s", imp, content[:50])

    return saved