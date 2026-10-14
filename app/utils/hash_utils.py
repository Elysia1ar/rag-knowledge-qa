"""哈希工具，用于增量入库的幂等判断。"""
import hashlib
from pathlib import Path


def md5_text(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def md5_file(path: str | Path, chunk_size: int = 1 << 20) -> str:
    """对大文件流式计算 MD5，避免一次性读入内存。"""
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()