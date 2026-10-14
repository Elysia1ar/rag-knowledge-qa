"""索引管理业务：全量重建、批量重建。

重建流程：
  1. 遍历 data/raw/ 下所有支持的文件
  2. 对每个文件：删除旧向量 → 分块 → Embedding → 写入
  3. 每次处理完一个文件，上报一次进度
"""
import asyncio
from pathlib import Path

from app.core.logging import get_logger
from app.rag.pipeline.index_pipeline import index_file
from app.services.task_manager import TaskContext
from app.utils.file_utils import list_raw_files


logger = get_logger(__name__)


async def rebuild_all(ctx: TaskContext) -> dict:
    """全量重建所有文档索引。"""
    files = list_raw_files()
    ctx.set_total(len(files))
    ctx.update(0, f"共 {len(files)} 个文件待处理")

    total_chunks = 0
    processed = 0
    failed: list[str] = []

    for i, path in enumerate(files, start=1):
        ctx.check_cancel()

        try:
            n = await asyncio.to_thread(index_file, path, force=True)
            total_chunks += n
        except Exception as e:  # noqa: BLE001
            logger.warning("重建失败：%s | %s", path.name, e)
            failed.append(path.name)

        processed = i
        ctx.update(processed, f"已处理 {processed}/{len(files)}：{path.name}")

    return {
        "total_files": len(files),
        "processed": processed,
        "total_chunks": total_chunks,
        "failed": failed,
    }


async def rebuild_single(ctx: TaskContext, file_path: str) -> dict:
    """重建单个文件。"""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在：{file_path}")

    ctx.set_total(1)
    ctx.update(0, f"处理 {path.name}")

    n = await asyncio.to_thread(index_file, path, force=True)
    ctx.update(1, f"完成：{path.name}")

    return {"file": path.name, "chunks": n}