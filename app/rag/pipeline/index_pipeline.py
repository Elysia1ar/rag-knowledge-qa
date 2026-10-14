"""索引管线：加载 → 分块 → 向量化 → 入库。

支持幂等增量入库：以文件 MD5 作为文档指纹，已入库且未修改的文件跳过。
"""
from dataclasses import dataclass
from pathlib import Path

from langchain_core.documents import Document

from app.core.config import get_settings
from app.core.logging import get_logger
from app.rag.loaders import load_directory, load_single_file
from app.rag.splitter import split_documents
from app.rag.vectorstore import add_documents, delete_by_source, get_vectorstore
from app.utils.file_utils import list_raw_files
from app.utils.hash_utils import md5_file

from app.rag.retrievers.bm25_retriever import invalidate_cache

logger = get_logger(__name__)


@dataclass
class IndexReport:
    total_files: int = 0
    indexed_files: int = 0
    skipped_files: int = 0
    total_chunks: int = 0


_FINGERPRINT_META_KEY = "file_md5"


def _existing_fingerprints() -> dict[str, str]:
    """从 Chroma 读取已入库文件指纹。"""
    vs = get_vectorstore()
    try:
        data = vs.get(include=["metadatas"])
    except Exception:
        return {}

    fps: dict[str, str] = {}
    for meta in data.get("metadatas", []) or []:
        src = meta.get("source")
        md5 = meta.get(_FINGERPRINT_META_KEY)
        if src and md5:
            fps[src] = md5
    return fps


def index_file(path: str | Path, *, force: bool = False) -> int:
    """入库单个文件，返回写入 chunk 数量。"""
    p = Path(path)
    file_md5 = md5_file(p)

    if not force:
        existing = _existing_fingerprints().get(str(p))
        if existing == file_md5:
            logger.info("跳过未修改文件: %s", p.name)
            return 0

    # 删旧
    delete_by_source(str(p))

    docs = load_single_file(p)
    chunks = split_documents(docs)

    for c in chunks:
        c.metadata[_FINGERPRINT_META_KEY] = file_md5
        c.metadata["source"] = str(p)

    ids = [c.metadata["chunk_id"] for c in chunks]
    add_documents(chunks, ids=ids)
    invalidate_cache()          # ← 新增
    logger.info("入库 %s，%d chunks", p.name, len(chunks))
    return len(chunks)


def index_directory(directory: str | Path | None = None, *,
                    force: bool = False) -> IndexReport:
    """批量入库目录下所有文档。"""
    s = get_settings()
    directory = Path(directory) if directory else s.raw_dir

    files = [p for p in list_raw_files() if p.is_relative_to(directory)]

    report = IndexReport(total_files=len(files))
    for p in files:
        n = index_file(p, force=force)
        if n == 0:
            report.skipped_files += 1
        else:
            report.indexed_files += 1
            report.total_chunks += n

    logger.info(
        "索引完成 | 文件 %d | 新增 %d | 跳过 %d | chunk %d",
        report.total_files, report.indexed_files,
        report.skipped_files, report.total_chunks,
    )
    return report
