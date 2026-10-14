FROM python:3.11-slim

# 从官方镜像复制 uv 二进制
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# 系统依赖：curl 用于 HEALTHCHECK，libgomp1 是 torch 运行时需要的
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    HF_ENDPOINT=https://hf-mirror.com \
    HF_HOME=/app/data/hf_cache \
    HF_HUB_DISABLE_SYMLINKS_WARNING=1

# 先只复制依赖描述文件，最大化缓存命中
COPY pyproject.toml uv.lock ./

# 用 cache mount 让 uv 下载缓存独立于镜像层，不打进镜像也不占 Build Cache
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# 复制应用代码
COPY app ./app
COPY scripts ./scripts
COPY data/eval/golden_set.jsonl ./data/eval/golden_set.jsonl

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
    CMD curl -fsS http://localhost:8000/api/v1/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]