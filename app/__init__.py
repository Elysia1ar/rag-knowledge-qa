"""应用包初始化。

必须保证 HF 相关环境变量在任何第三方库导入之前完成设置，
否则 huggingface_hub 会把 ENDPOINT 固化为默认的 huggingface.co。
"""
import os
from pathlib import Path


_ROOT = Path(__file__).resolve().parents[1]
_HF_CACHE = _ROOT / "data" / "hf_cache"

# ---- HuggingFace 镜像与缓存（必须在所有 app.* 导入之前）----
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
os.environ.setdefault("HF_HOME", str(_HF_CACHE))
os.environ.setdefault("TRANSFORMERS_CACHE", str(_HF_CACHE / "transformers"))
os.environ.setdefault("SENTENCE_TRANSFORMERS_HOME", str(_HF_CACHE / "sentence_transformers"))
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
os.environ.setdefault("JIEBA_CACHE_DIR", str(_ROOT / "data" / "jieba_cache"))

