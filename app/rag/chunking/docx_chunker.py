"""Word 文档切分：按标题样式切分。

设计说明：
  - 输入是 UnstructuredWordDocumentLoader 的输出——每段一个 Document，
    元数据里带 category（Title / Heading / NarrativeText / ListItem / Table ...）
  - 按 category 识别标题，用栈维护层级，构造 heading_path
  - 相邻的正文段落合并到同一个 section，减少碎片
  - 超大 section 用递归分隔符二次切
"""
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import get_settings
from app.core.logging import get_logger
from app.rag.chunking.base import BaseChunker


logger = get_logger(__name__)


# Unstructured 识别出的标题类别（不同版本可能略有差异，全部覆盖）
_TITLE_CATEGORIES = {
    "Title",
    "Heading",
    "Heading1", "Heading2", "Heading3", "Heading4",
}


class DocxChunker(BaseChunker):
    file_type = "docx"

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
        # 1. 按 category 归组为 (heading_path, content) 列表
        sections = self._group_by_heading(docs)

        # 2. 对每个 section 决定是否二次切
        result: list[Document] = []
        base_source = docs[0].metadata.get("source") if docs else None

        for heading_path, content, sample_meta in sections:
            meta = dict(sample_meta)
            meta["heading_path"] = heading_path
            meta["file_type"] = "docx"
            if base_source:
                meta.setdefault("source", base_source)

            if len(content) <= self.chunk_size * 1.5:
                result.append(Document(page_content=content, metadata=meta))
            else:
                sub_docs = self.fallback_splitter.create_documents(
                    [content],
                    metadatas=[meta],
                )
                result.extend(sub_docs)

        logger.debug("DOCX 切分完成：%d 段 → %d chunk", len(docs), len(result))
        return result

    def _group_by_heading(
        self,
        docs: list[Document],
    ) -> list[tuple[str, str, dict]]:
        """把段落按标题归组。

        Returns:
            [(heading_path, merged_content, sample_metadata), ...]
        """
        sections: list[tuple[str, str, dict]] = []
        stack: list[str] = []
        buffer: list[str] = []

        def flush_buffer() -> None:
            """把当前 buffer 里的段落合并成一个 section。"""
            if not buffer:
                return
            content = "\n\n".join(buffer).strip()
            if content:
                heading_path = " > ".join(stack) if stack else ""
                # 用 buffer 第一条的 metadata 作为 sample
                # 这里简化处理，后面统一用第一个 doc 的元数据
                sections.append((heading_path, content, {}))
            buffer.clear()

        for doc in docs:
            content = (doc.page_content or "").strip()
            if not content:
                continue

            category = (doc.metadata.get("category") or "").strip()

            if category in _TITLE_CATEGORIES:
                flush_buffer()
                level = self._level_of(doc.metadata, content)   # ← 传 doc.metadata
                stack = stack[: level - 1]
                stack.append(content)
            else:
                buffer.append(content)

        flush_buffer()   # 收尾

        # 为每个 section 附上第一个 doc 的 metadata（用于溯源）
        if docs:
            base_meta = {k: v for k, v in docs[0].metadata.items()
                         if k not in ("category",)}
            sections = [
                (hp, content, base_meta)
                for hp, content, _ in sections
            ]

        return sections

    @staticmethod
    def _level_of(meta: dict, content: str) -> int:
        """判断标题层级。

        优先级：
          1. style_level —— loader 从 python-docx 读取的 Heading N 样式
          2. category 里的数字
          3. 内容启发式
        """
        # 1. 最可靠：python-docx 读到的样式层级
        lvl = meta.get("style_level")
        if isinstance(lvl, int) and lvl > 0:
            return lvl

        # 2. category 里带数字
        category = (meta.get("category") or "").strip()
        for ch in category:
            if ch.isdigit():
                return int(ch)

        # 3. 内容启发式（兜底）
        stripped = content.lstrip()
        parts = stripped.split(None, 1)
        prefix = parts[0].rstrip(".、") if parts else ""

        if "." in prefix:
            return prefix.count(".") + 1

        if len(prefix) == 1 and prefix in "一二三四五六七八九十":
            return 2

        if prefix.startswith("（") and prefix.rstrip("）") in (
            "一", "二", "三", "四", "五",
        ):
            return 2

        if prefix.isdigit():
            return 1

        return 1