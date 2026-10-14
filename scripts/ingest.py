"""命令行批量入库脚本。

用法:
    python -m scripts.ingest                  # 增量入库 data/raw/
    python -m scripts.ingest --force          # 强制全量重建
    python -m scripts.ingest --file xxx.pdf   # 单文件入库
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.logging import setup_logging  # noqa: E402
from app.rag.pipeline.index_pipeline import (  # noqa: E402
    index_directory,
    index_file,
)


def main() -> None:
    setup_logging()

    parser = argparse.ArgumentParser(description="RAG 文档入库")
    parser.add_argument("--dir", type=str, default=None, help="文档目录，默认 data/raw")
    parser.add_argument("--file", type=str, default=None, help="单文件入库")
    parser.add_argument("--force", action="store_true", help="忽略指纹，强制重建")
    args = parser.parse_args()

    if args.file:
        n = index_file(args.file, force=args.force)
        print(f"✅ 入库 {args.file}，{n} chunks")
        return

    report = index_directory(args.dir, force=args.force)
    print(
        f"✅ 索引完成\n"
        f"   文件总数 : {report.total_files}\n"
        f"   新增入库 : {report.indexed_files}\n"
        f"   跳过未变 : {report.skipped_files}\n"
        f"   chunk 数 : {report.total_chunks}"
    )


if __name__ == "__main__":
    main()