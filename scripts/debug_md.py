"""诊断 MarkdownHeaderTextSplitter 的实际行为。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from langchain_text_splitters import MarkdownHeaderTextSplitter


def main() -> None:
    path = Path("data/raw/rag_design_guide.md")
    text = path.read_text(encoding="utf-8")

    # 打印前 200 字符的原始字节，检查 BOM 和换行符
    print("=== 文件前 200 字节（repr）===")
    print(repr(text[:200]))
    print()

    print("=== 是否有 BOM ===")
    print(f"text.startswith('\\ufeff'): {text.startswith(chr(0xFEFF))}")
    print()

    print("=== 换行符统计 ===")
    print(f"\\r\\n 数量: {text.count(chr(13) + chr(10))}")
    print(f"\\n   数量: {text.count(chr(10))}")
    print()

    splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[
            ("#", "h1"),
            ("##", "h2"),
            ("###", "h3"),
        ],
        strip_headers=False,
    )

    sections = splitter.split_text(text)
    print(f"=== 切分结果：{len(sections)} 个 section ===")
    for i, sec in enumerate(sections, 1):
        print(f"\n[{i}] metadata = {sec.metadata}")
        print(f"    content[:100] = {sec.page_content[:100]!r}")


if __name__ == "__main__":
    main()