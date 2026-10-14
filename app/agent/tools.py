"""Agent 工具集。

工具设计原则：
  1. docstring 写"何时使用"，而不是"是什么"——LLM 靠这段判断调用时机
  2. 返回值统一为字符串（LLM 友好），结构化信息序列化为 JSON
  3. 单个工具保持幂等、无副作用
"""
import json
from datetime import datetime

from langchain_core.tools import tool

from app.core.logging import get_logger
from app.rag.retrievers import hybrid_search, rerank


logger = get_logger(__name__)


@tool
def search_knowledge(query: str) -> str:
    """在知识库中检索与问题相关的文档片段。

    当用户提出的问题需要依据知识库内容回答时，使用此工具。
    输入应为一个独立、完整的问题或查询语句，不要包含"那"、"它"等指代词。
    返回若干条最相关的文档片段及其来源，可用于回答用户问题。

    对于复杂问题，可以拆分成多个子问题多次调用本工具，以获得更全面的信息。
    """
    from app.core.config import get_settings

    settings = get_settings()
    logger.info("[tool] search_knowledge | query=%s", query[:60])

    try:
        candidates = hybrid_search(query)
        contexts = rerank(query, candidates, top_k=settings.final_top_k)
    except Exception as e:
        logger.exception("search_knowledge 失败")
        return f"检索失败：{e}"

    if not contexts:
        return "知识库中没有找到相关内容。"

    lines = []
    for i, doc in enumerate(contexts, 1):
        src = doc.metadata.get("file_name") or doc.metadata.get("source", "unknown")
        score = doc.metadata.get("rerank_score", 0)
        lines.append(
            f"[{i}] 来源: {src} (相关度: {score:.4f})\n"
            f"{doc.page_content.strip()}"
        )

    return "\n\n".join(lines)


@tool
def get_current_time() -> str:
    """获取当前的日期和时间。

    当用户询问"现在几点"、"今天几号"、"当前时间"等与时间相关的问题时，使用此工具。
    """
    now = datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S (%A)")


@tool
def list_documents() -> str:
    """列出知识库中已有的所有文档名称。

    当用户询问"知识库里有什么"、"有哪些文档"、"能不能查到关于 X 的资料"时，
    使用此工具帮助用户了解知识库的范围。
    """
    from app.core.config import get_settings
    from app.utils.file_utils import list_raw_files

    settings = get_settings()
    files = list_raw_files()

    if not files:
        return "知识库当前为空。"

    names = [p.name for p in files]
    return json.dumps(
        {"total": len(names), "files": names},
        ensure_ascii=False,
    )


# 导出工具列表，Agent 初始化时使用
ALL_TOOLS = [search_knowledge, get_current_time, list_documents]