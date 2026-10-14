"""文本分块：按文件类型分发到对应 chunker。

对外统一入口是 split_documents()，内部根据 metadata.file_type
自动选择 chunker，并统一写入 chunk_id / chunk_index。
"""
from collections import defaultdict

from langchain_core.documents import Document

from app.core.logging import get_logger
from app.rag.chunking import CHUNKER_MAP
from app.rag.chunking.base import BaseChunker
from app.rag.chunking.txt_chunker import TxtChunker
from app.utils.hash_utils import md5_text


logger = get_logger(__name__)


def split_documents(docs: list[Document]) -> list[Document]:
    """按 file_type 分组，分发到不同 chunker，统一补 chunk_id。"""
    if not docs:
        return []

    # 1. 按 file_type 分组
    by_type: dict[str, list[Document]] = defaultdict(list)
    for d in docs:
        ft = (d.metadata.get("file_type") or "txt").lower()
        by_type[ft].append(d)

    # 2. 每类走对应 chunker
    all_chunks: list[Document] = []
    for ft, group in by_type.items():
        chunker_cls = CHUNKER_MAP.get(ft)
        if not chunker_cls:
            logger.warning("未注册 file_type=%s，回退到 TxtChunker", ft)
            chunker_cls = TxtChunker

        chunker: BaseChunker = chunker_cls()
        chunks = chunker.split(group)
        logger.info(
            "chunker=%s | 输入 %d 篇 | 输出 %d chunk",
            chunker_cls.__name__, len(group), len(chunks),
        )
        all_chunks.extend(chunks)

    # 3. 统一写 chunk_id / chunk_index
    for idx, chunk in enumerate(all_chunks):
        chunk.metadata["chunk_index"] = idx
        chunk.metadata["chunk_id"] = md5_text(
            f"{chunk.metadata.get('source', '')}"
            f"::{chunk.metadata.get('page', 0)}"
            f"::{chunk.metadata.get('heading_path', '')}"
            f"::{idx}"
            f"::{chunk.page_content}"
        )

    logger.info("分块完成，共 %d 个 chunk", len(all_chunks))
    return all_chunks


def build_splitter(
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
):
    """兼容旧接口，返回 TxtChunker 内部的 splitter。"""
    return TxtChunker(chunk_size, chunk_overlap).splitter