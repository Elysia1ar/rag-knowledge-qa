"""Embedding 冒烟测试：验证 HF 镜像与模型加载是否正常。"""
import os
import sys
from pathlib import Path

# 把项目根目录加入 sys.path，让脚本能被直接执行
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# 必须在导入 transformers / sentence_transformers 之前设置
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

from app.core.config import get_settings  # noqa: E402
from app.rag.embeddings import get_embeddings  # noqa: E402


def main() -> None:
    settings = get_settings()
    print(f"HF_ENDPOINT = {os.environ.get('HF_ENDPOINT')}")
    print(f"模型        = {settings.embedding_model}")
    print(f"设备        = {settings.embedding_device}")
    print("正在加载模型（首次会下载，可能需要 1-3 分钟）...")

    emb = get_embeddings()
    vec = emb.embed_query("RAG 是什么？")
    print(f"\n✅ 加载成功")
    print(f"向量维度 : {len(vec)}")
    print(f"前 5 维  : {vec[:5]}")


if __name__ == "__main__":
    main()