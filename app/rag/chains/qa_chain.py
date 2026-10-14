"""RAG 问答链：上下文拼装 + LLM 生成 + 引用解析。"""
from dataclasses import dataclass, field
#上下文格式化
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser

from app.core.config import get_settings
from app.core.logging import get_logger
from app.rag.chains.prompt_templates import QA_PROMPT
from app.rag.llm import get_llm
from app.rag.retrievers import hybrid_search, rerank

import asyncio

from dataclasses import dataclass, field
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from app.rag.chains.prompt_templates import build_qa_prompt

logger = get_logger(__name__)


@dataclass
class QAResult:
    answer: str
    sources: list[dict] = field(default_factory=list)
    contexts: list[Document] = field(default_factory=list)


def _format_context(docs: list[Document], max_chars: int) -> tuple[str, list[dict]]:
    """把检索结果拼成带编号的上下文，并生成可追溯的 sources 列表。"""
    lines: list[str] = []
    sources: list[dict] = []
    total = 0

    for i, d in enumerate(docs, start=1):
        text = d.page_content.strip()
        if total + len(text) > max_chars:
            break
        total += len(text)

        meta = d.metadata
        source_name = meta.get("file_name") or meta.get("source", "unknown")

        # 拼上下文时把章节/页码也带上，让 LLM 也能感知来源结构
        locator = _build_locator(meta)
        header = f"[{i}] 来源：{source_name}"
        if locator:
            header += f"（{locator}）"
        lines.append(f"{header}\n{text}\n")

        sources.append({
            "index": i,
            "source": meta.get("source"),
            "file_name": source_name,
            "file_type": meta.get("file_type"),
            "chunk_id": meta.get("chunk_id"),
            "page": meta.get("page"),
            "heading_path": meta.get("heading_path"),
            "preview": text[:80].replace("\n", " "),
            "rerank_score": meta.get("rerank_score"),
        })

    return "\n".join(lines), sources


def _build_locator(meta: dict) -> str:
    """根据元数据生成人类可读的定位信息。

    - PDF: "第 3 页"
    - MD/Word: heading_path 最后一级
    - TXT: 空
    """
    file_type = (meta.get("file_type") or "").lower()

    if file_type == "pdf":
        page = meta.get("page")
        if isinstance(page, int):
            return f"第 {page + 1} 页"      # page 是 0-based
        return ""

    heading = meta.get("heading_path")
    if heading:
        # 只取最后一级，避免上下文过长
        return str(heading).split(" > ")[-1]

    return ""


def _strip_sources_from_answer(answer: str) -> str:
    """可选：把 [1] 之类的引用标记保留在答案里，不剥离。"""
    return answer.strip()


def answer_question(
    question: str,
    *,
    top_k: int | None = None,
    return_contexts: bool = False,
    memory_block: str = "",
) -> QAResult:
    """完整问答流程：混合检索 → 重排 → 拼 Prompt → LLM 生成。"""
    s = get_settings()
    top_k = top_k or s.final_top_k

    candidates = hybrid_search(question)
    contexts = rerank(question, candidates, top_k=top_k)

    # ---- 拒答拦截 1：检索无结果 ----
    if not contexts:
        logger.warning("检索无结果，走兜底回答")
        return QAResult(
            answer="根据现有知识库，我无法回答该问题。",
            sources=[],
            contexts=[] if return_contexts else [],
        )

    # ---- 拒答拦截 2：Top-1 分数低于阈值 ----
    top_score = float(contexts[0].metadata.get("rerank_score", 0.0))
    if top_score < s.rerank_threshold:
        logger.info(
            "Top-1 rerank=%.4f < 阈值 %.4f，直接拒答 | query=%s",
            top_score, s.rerank_threshold, question[:40],
        )
        return QAResult(
            answer="根据现有知识库，我无法回答该问题。",
            sources=[],
            contexts=[] if return_contexts else [],
        )

    context_str, sources = _format_context(contexts, s.qa_context_max_chars)

    from app.rag.chains.prompt_templates import build_qa_prompt

    llm = get_llm()
    prompt = build_qa_prompt(memory_block)
    chain = prompt | llm | StrOutputParser()
    answer = chain.invoke({"context": context_str, "question": question})

    logger.info("生成完成 | 上下文=%d 条 | 答案长度=%d",
                len(contexts), len(answer))

    return QAResult(
        answer=_strip_sources_from_answer(answer),
        sources=sources,
        contexts=contexts if return_contexts else [],
    )

# ---------- 新增：异步流式问答 ----------

async def astream_answer(
    question: str,
    *,
    top_k: int | None = None,
    memory_block: str = "",
):
    """异步流式问答生成器。

    yield 结构： (event: str, data: Any)
      ("sources", list[dict])  检索完成，返回引用来源
      ("token",   str)         LLM 输出的 token 片段
      ("done",    None)        生成完成

    设计说明：
    - 检索与重排是同步 CPU 密集操作，通过 asyncio.to_thread 移出事件循环
    - 生成阶段使用 chain.astream()，直接转发 LLM 的真 token
    - 拒答时也走流式，前端体验一致
    """
    s = get_settings()
    top_k = top_k or s.final_top_k

    # 1) 检索 + 重排（同步 → 线程池）
    candidates = await asyncio.to_thread(hybrid_search, question)
    contexts = await asyncio.to_thread(rerank, question, candidates, top_k=top_k)

    # 2) 拒答拦截（保持与同步版一致）
    top_score = float(contexts[0].metadata.get("rerank_score", 0.0)) if contexts else 0.0
    if not contexts or top_score < s.rerank_threshold:
        logger.info(
            "流式：Top-1 rerank=%.4f < 阈值 %.4f，直接拒答",
            top_score, s.rerank_threshold,
        )
        yield ("sources", [])
        yield ("token", "根据现有知识库，我无法回答该问题。")
        yield ("done", None)
        return

    # 3) 拼上下文 + 上报来源
    context_str, sources = _format_context(contexts, s.qa_context_max_chars)
    yield ("sources", sources)

    # 4) 真流式生成
    prompt = build_qa_prompt(memory_block)
    chain = prompt | get_llm() | StrOutputParser()
    async for chunk in chain.astream({"context": context_str, "question": question}):
        # chunk 经过 StrOutputParser 后是 str
        if chunk:
            yield ("token", chunk)

    yield ("done", None)