"""PDF 切分：按页处理。

设计说明：
  - PyPDFLoader 已经按页输出 Document，每个 Document 就是一页
  - 页内长度合适时直接保留整页；超限时页内递归二次切
  - 所有输出都保留 page 元数据，支持"跳到第 N 页"式溯源
"""
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import get_settings
from app.core.logging import get_logger
from app.rag.chunking.base import BaseChunker


logger = get_logger(__name__)


class PdfChunker(BaseChunker):
    file_type = "pdf"

    def __init__(
        self,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ) -> None:
        s = get_settings()
        self.chunk_size = chunk_size or s.chunk_size
        self.chunk_overlap = chunk_overlap or s.chunk_overlap

        self.fallback_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", "。", "！", "？", "；",
                        ".", "!", "?", ";", " ", ""],
        )

    def split(self, docs: list[Document]) -> list[Document]:
        """docs 通常是「每页一个 Document」。

        但一份 PDF 可能有几百页，这里逐个处理。
        """
        result: list[Document] = []

        for doc in docs:
            content = (doc.page_content or "").strip()
            if not content:
                continue

            # 保留原 metadata（含 page / source），补齐 file_type
            base_meta = dict(doc.metadata)
            base_meta["file_type"] = "pdf"
            base_meta.setdefault("page", 0)

            # 页内长度合适：整页作一个 chunk
            if len(content) <= self.chunk_size * 1.5:
                result.append(Document(
                    page_content=content,
                    metadata=base_meta,
                ))
            else:
                # 页内超限：递归二次切，每片保留原 page 号
                sub_docs = self.fallback_splitter.create_documents(
                    [content],
                    metadatas=[base_meta],
                )
                result.extend(sub_docs)

        logger.debug("PDF 切分完成：%d 页 → %d chunk", len(docs), len(result))
        return result