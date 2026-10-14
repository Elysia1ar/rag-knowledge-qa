"""全局配置，基于 pydantic-settings，从 .env 读取。"""
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- App ----
    app_name: str = "rag-knowledge-qa"
    app_env: Literal["dev", "prod", "test"] = "dev"
    debug: bool = True
    log_level: str = "INFO"

    # ---- Paths ----
    base_dir: Path = BASE_DIR
    data_dir: Path = BASE_DIR / "data"
    raw_dir: Path = BASE_DIR / "data" / "raw"
    processed_dir: Path = BASE_DIR / "data" / "processed"
    chroma_dir: Path = BASE_DIR / "data" / "chroma"
    hf_home: Path = BASE_DIR / "data" / "hf_cache"
    eval_dir: Path = BASE_DIR / "data" / "eval"

    # ---- Splitter ----
    chunk_size: int = 512
    chunk_overlap: int = 64

    # ---- Embedding ----
    embedding_provider: Literal["huggingface", "openai"] = "huggingface"
    embedding_model: str = "BAAI/bge-small-zh-v1.5"
    embedding_device: str = "cpu"
    embedding_batch_size: int = 32
    openai_api_key: str | None = None
    openai_base_url: str | None = None

    # ---- HF 镜像 ----
    hf_endpoint: str = "https://hf-mirror.com"

    # ---- Vector Store ----
    chroma_collection: str = "rag_knowledge"

    # ---- Retrieval ----
    vector_top_k: int = 20              # 向量召回数
    bm25_top_k: int = 20                # BM25 召回数
    rrf_k: int = 60                     # RRF 平滑常数
    hybrid_top_k: int = 10              # 融合后送入 rerank 的数量
    final_top_k: int = 5                # 最终返回数量

    # ---- Reranker ----
    reranker_enabled: bool = True
    reranker_model: str = "BAAI/bge-reranker-base"
    rerank_threshold: float = 0.1          # ← 新增：Top-1 低于此值直接拒答

    # 字段
    bm25_cache: Path = BASE_DIR / "data" / "bm25_index.pkl"

    # ---- LLM ----
    llm_provider: Literal["deepseek", "openai", "qwen"] = "deepseek"
    llm_model: str = "deepseek-chat"
    llm_api_key: str | None = None
    llm_base_url: str = "https://api.deepseek.com"
    llm_temperature: float = 0.1
    llm_max_tokens: int = 2048

    # ---- QA Chain ----
    qa_context_max_chars: int = 6000       # 拼进 Prompt 的上下文总上限

    # ---- Memory ----
    memory_buffer_size: int = 12            # 最近 N 条消息作为 buffer（6 轮）
    memory_summary_threshold: int = 16      # 超过 N 条触发摘要压缩
    memory_summary_max_chars: int = 400     # 摘要长度上限
    memory_extract_enabled: bool = True         # 是否启用自动提取
    memory_min_importance: float = 0.4          # 低于此分数不保存
    memory_search_min_importance: float = 0.3   # 检索时最低重要性
    memory_extract_rounds: int = 2              # 每 N 轮触发一次提取
    memory_search_min_similarity: float = 0.55       # 绝对下限：过滤无关记忆
    memory_search_min_ratio: float = 0.92            # 相对下限：与 Top-1 至少差 8% 才保留
    memory_search_max_results: int = 3               # 硬上限
    memory_consolidate_enabled: bool = True     # 是否启用固化
    memory_dedup_threshold: float = 0.85         # 语义去重阈值
    memory_forget_max_age_days: int = 90         # 时间衰减天数
    memory_forget_min_importance: float = 0.5    # 时间衰减的重要性下限
    memory_max_per_user: int = 500               # 容量上限
    
    # ---- Database ----
    db_url: str = f"sqlite+aiosqlite:///{BASE_DIR / 'data' / 'app.db'}"
    db_echo: bool = False

    # ---- Server ----
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list[str] = ["*"]

    # ---- Auth ----
    jwt_secret: str = "change-me-in-production-please-use-random-string"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7         # 7 天

    default_admin_username: str = "admin"
    default_admin_password: str = "admin123"

    # ---- Agent ----
    agent_max_iterations: int = 8             # ReAct 最大循环次数
    agent_temperature: float = 0.0            # Agent 决策要稳，用 0

    # ensure_dirs 里加上父目录
    def ensure_dirs(self) -> None:
        for p in (
            self.data_dir, self.raw_dir, self.processed_dir,
            self.chroma_dir, self.hf_home, self.eval_dir):
            p.mkdir(parents=True, exist_ok=True)
        self.bm25_cache.parent.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.ensure_dirs()
    return s