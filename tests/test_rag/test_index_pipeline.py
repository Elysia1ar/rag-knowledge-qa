from pathlib import Path

from langchain_core.documents import Document

from app.rag.splitter import split_documents


def test_split_documents_writes_metadata():
    docs = [Document(
        page_content="RAG。检索增强生成。" * 200,
        metadata={"source": "unit.txt", "page": 0},
    )]
    chunks = split_documents(docs)

    assert len(chunks) >= 2
    for c in chunks:
        assert "chunk_id" in c.metadata
        assert "chunk_index" in c.metadata
        assert len(c.page_content) <= 600


def test_splitter_respects_chinese_separators():
    text = "第一段内容。" * 50 + "\n\n" + "第二段内容。" * 50
    docs = [Document(page_content=text, metadata={"source": "unit.txt"})]
    chunks = split_documents(docs)
    assert all(chunk.page_content.strip() for chunk in chunks)