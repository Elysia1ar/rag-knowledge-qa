"""分块策略验证：展示不同文件类型的分块效果。

用法：
    python -m scripts.check_chunking
    python -m scripts.check_chunking data/raw/rag_design_guide.md
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.logging import setup_logging
from app.rag.loaders import load_single_file
from app.rag.splitter import split_documents


def show_chunks(path: str) -> None:
    print(f"\n{'=' * 72}\n📄 {path}\n{'=' * 72}")
    docs = load_single_file(path)
    chunks = split_documents(docs)

    print(f"\n共 {len(chunks)} 个 chunk\n")
    for i, c in enumerate(chunks, 1):
        meta = c.metadata
        heading = meta.get("heading_path") or "-"
        page = meta.get("page", "-")
        print(f"[{i}] type={meta.get('file_type')} | page={page}")
        print(f"    heading_path: {heading}")
        preview = c.page_content[:150].replace("\n", " ")
        print(f"    {preview}...")
        print()


def main() -> None:
    setup_logging()
    files = sys.argv[1:] if len(sys.argv) > 1 else [
        "data/raw/rag_intro.txt",
        "data/raw/rag_design_guide.md",
    ]
    for f in files:
        if not Path(f).exists():
            print(f"⚠️  文件不存在：{f}")
            continue
        show_chunks(f)


if __name__ == "__main__":
    main()