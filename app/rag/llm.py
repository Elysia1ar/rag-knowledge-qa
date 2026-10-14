"""LLM 客户端封装，统一走 OpenAI 兼容协议（DeepSeek/Qwen/OpenAI 均适用）。"""
from functools import lru_cache

from langchain_openai import ChatOpenAI

from app.core.config import get_settings
from app.core.logging import get_logger


logger = get_logger(__name__)


_PROVIDER_DEFAULTS = {
    "deepseek": "https://api.deepseek.com",
    "qwen":     "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "openai":   "https://api.openai.com/v1",
}


@lru_cache
def get_llm() -> ChatOpenAI:
    s = get_settings()
    if not s.llm_api_key:
        raise ValueError("请在 .env 中设置 LLM_API_KEY")

    base_url = s.llm_base_url or _PROVIDER_DEFAULTS.get(s.llm_provider)
    logger.info("初始化 LLM: provider=%s model=%s", s.llm_provider, s.llm_model)

    return ChatOpenAI(
        model=s.llm_model,
        api_key=s.llm_api_key,
        base_url=base_url,
        temperature=s.llm_temperature,
        max_tokens=s.llm_max_tokens,
        streaming=True,          # 为后续流式输出预留
    )