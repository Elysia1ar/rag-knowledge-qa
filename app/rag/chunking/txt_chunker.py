"""纯文本切分：递归分隔符策略（迁移自原 splitter.py）。"""
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import get_settings
from app.rag.chunking.base import BaseChunker


# 优先级从高到低：段落 → 换行 → 中文句末 → 英文句末 → 逗号 → 空格
_CN_SEPARATORS = [
    "\n\n", "\n",
    "。", "！", "？", "；",
    ".", "!", "?", ";",
    "，", ",",
    " ", "",
]


class TxtChunker(BaseChunker):
    file_type = "txt"

    def __init__(
        self,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ) -> None:
        s = get_settings()
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size or s.chunk_size,
            chunk_overlap=chunk_overlap or s.chunk_overlap,
            separators=_CN_SEPARATORS,
            length_function=len,
            is_separator_regex=False,
        )

    def split(self, docs: list[Document]) -> list[Document]:
        result: list[Document] = []
        for doc in docs:
            sub = self.splitter.split_documents([doc])
            result.extend(sub)
        return result