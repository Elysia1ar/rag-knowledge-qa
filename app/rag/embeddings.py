"""Embedding 模型封装，支持 HuggingFace 与 OpenAI 兼容接口。"""
from functools import lru_cache

from langchain_core.embeddings import Embeddings

from app.core.config import get_settings
from app.core.logging import get_logger


logger = get_logger(__name__)


@lru_cache
def get_embeddings() -> Embeddings:
    s = get_settings()

    if s.embedding_provider == "huggingface":
        from langchain_huggingface import HuggingFaceEmbeddings

        logger.info("使用 HuggingFace Embedding: %s (%s)",
                    s.embedding_model, s.embedding_device)
        return HuggingFaceEmbeddings(
            model_name=s.embedding_model,
            model_kwargs={"device": s.embedding_device},
            encode_kwargs={"normalize_embeddings": True,
                           "batch_size": s.embedding_batch_size},
        )

    if s.embedding_provider == "openai":
        from langchain_openai import OpenAIEmbeddings

        if not s.openai_api_key:
            raise ValueError("EMBEDDING_PROVIDER=openai 时必须设置 OPENAI_API_KEY")
        logger.info("使用 OpenAI Embedding: %s", s.embedding_model)
        return OpenAIEmbeddings(
            model=s.embedding_model,
            api_key=s.openai_api_key,
            base_url=s.openai_base_url,
        )

    raise ValueError(f"未知的 embedding_provider: {s.embedding_provider}")