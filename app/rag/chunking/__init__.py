"""Chunker 注册表。

新增文件类型只需：
  1. 实现一个 BaseChunker 子类
  2. 在 CHUNKER_MAP 里注册
  3. 在 loaders.py 里补 metadata.file_type
"""
from app.rag.chunking.base import BaseChunker
from app.rag.chunking.docx_chunker import DocxChunker
from app.rag.chunking.md_chunker import MdChunker
from app.rag.chunking.txt_chunker import TxtChunker
from app.rag.chunking.pdf_chunker import PdfChunker

CHUNKER_MAP: dict[str, type[BaseChunker]] = {
    "txt": TxtChunker,
    "md": MdChunker,
    "pdf": PdfChunker,
    "docx": DocxChunker,
}


__all__ = ["BaseChunker", "TxtChunker", "MdChunker", "PdfChunker", "DocxChunker", "CHUNKER_MAP",]