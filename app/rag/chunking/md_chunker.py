"""Markdown 切分：按标题层级切。

设计说明：
  - 自己写正则切分，避免 MarkdownHeaderTextSplitter 的版本差异
  - 每个 section 的 heading_path 直接拼进 metadata
  - 超大 section 用递归分隔符二次切，每片都保留 heading_path
"""
import re

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import get_settings
from app.core.logging import get_logger
from app.rag.chunking.base import BaseChunker


logger = get_logger(__name__)


_HEADING_RE = re.compile(
    r"^(#{1,4})\s+(.+?)\s*$",
    re.MULTILINE,
)


class MdChunker(BaseChunker):
    file_type = "md"

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
        result: list[Document] = []
        for doc in docs:
            sections = self._split_by_heading(doc.page_content)

            for heading_path, content in sections:
                base_meta = dict(doc.metadata)
                base_meta["heading_path"] = heading_path
                base_meta["file_type"] = "md"

                if len(content) <= self.chunk_size * 1.5:
                    result.append(Document(
                        page_content=content,
                        metadata=base_meta,
                    ))
                else:
                    sub_docs = self.fallback_splitter.create_documents(
                        [content],
                        metadatas=[base_meta],
                    )
                    result.extend(sub_docs)

        logger.debug("MD 切分完成：%d 篇 → %d chunk", len(docs), len(result))
        return result

    def _split_by_heading(
        self,
        text: str,
    ) -> list[tuple[str, str]]:
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        headings: list[tuple[int, int, str]] = []
        for m in _HEADING_RE.finditer(text):
            level = len(m.group(1))
            title = m.group(2).strip()
            headings.append((m.start(), level, title))

        if not headings:
            return [("", text.strip())]

        sections: list[tuple[str, str]] = []
        stack: list[str] = []

        for i, (pos, level, title) in enumerate(headings):
            stack = stack[: level - 1]
            stack.append(title)
            heading_path = " > ".join(stack)

            content_start = pos
            content_end = (
                headings[i + 1][0] if i + 1 < len(headings) else len(text)
            )
            content = text[content_start:content_end].strip()
            if content:
                sections.append((heading_path, content))

        return sections