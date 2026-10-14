"""多轮对话问题改写：把依赖上下文的追问改写为独立问题。"""
from langchain_core.output_parsers import StrOutputParser
#多轮问题改写 
from app.core.logging import get_logger
from app.rag.chains.prompt_templates import CONDENSE_PROMPT
from app.rag.llm import get_llm


logger = get_logger(__name__)


def condense_question(question: str, chat_history: list[dict] | None = None) -> str:
    """无历史时直接返回原问题；有历史时调用 LLM 改写。"""
    if not chat_history:
        return question

    history_text = "\n".join(
        f"{m['role']}: {m['content']}" for m in chat_history[-6:]
    )

    chain = CONDENSE_PROMPT | get_llm() | StrOutputParser()
    rewritten = chain.invoke({
        "chat_history": history_text,
        "question": question,
    }).strip()

    logger.info("问题改写 | 原文=%s | 改写=%s", question[:40], rewritten[:40])
    return rewritten or question