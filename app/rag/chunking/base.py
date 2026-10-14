"""Chunker 抽象基类。

每个 chunker 负责一种文件类型的切分策略，输出统一为 list[Document]。
派生 chunker 应保证输出的 Document metadata 携带该类型特有的溯源字段，
例如 Markdown 的 heading_path、PDF 的 page。
"""
from abc import ABC, abstractmethod

from langchain_core.documents import Document


class BaseChunker(ABC):
    """文档切分器基类。"""

    file_type: str = "unknown"

    @abstractmethod
    def split(self, docs: list[Document]) -> list[Document]:
        """把一组同类型文档切分为更小的 chunk。"""
        raise NotImplementedError