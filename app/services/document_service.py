"""文档上传与索引编排。"""
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import RAGBaseError
from app.core.logging import get_logger
from app.db.models.document import Document as DocumentModel
from app.rag.pipeline.index_pipeline import index_file
from app.utils.file_utils import save_upload
from app.utils.hash_utils import md5_file

import asyncio


logger = get_logger(__name__)


async def upload_and_index(
    db: AsyncSession,
    file_name: str,
    content: bytes,
) -> tuple[DocumentModel, bool]:
    """保存文件 → 入库向量库 → 写元数据表。返回 (记录, 是否跳过)。"""
    path = save_upload(file_name, content)
    md5 = md5_file(path)

    existing = await db.execute(
        select(DocumentModel).where(DocumentModel.file_path == str(path))
    )
    record = existing.scalar_one_or_none()

    if record and record.file_md5 == md5:
        logger.info("文件未变，跳过：%s", path.name)
        return record, True

    chunk_count = index_file(path, force=True)

    if record:
        record.file_md5 = md5
        record.file_size = path.stat().st_size
        record.chunk_count = chunk_count
    else:
        record = DocumentModel(
            file_name=path.name,
            file_path=str(path),
            file_md5=md5,
            file_size=path.stat().st_size,
            file_type=path.suffix.lstrip("."),
            chunk_count=chunk_count,
        )
        db.add(record)

    await db.commit()
    await db.refresh(record)
    return record, False


async def list_documents(db: AsyncSession) -> list[DocumentModel]:
    result = await db.execute(select(DocumentModel).order_by(DocumentModel.id.desc()))
    return list(result.scalars().all())


async def delete_document(db: AsyncSession, doc_id: int) -> bool:
    record = await db.get(DocumentModel, doc_id)
    if not record:
        return False

    # 从向量库删除
    from app.rag.vectorstore import delete_by_source
    delete_by_source(record.file_path)

    # 物理文件删除
    try:
        Path(record.file_path).unlink(missing_ok=True)
    except OSError as e:
        logger.warning("物理文件删除失败：%s", e)

    await db.delete(record)
    await db.commit()
    return True

async def sync_from_disk(db: AsyncSession) -> dict:
    """扫描 data/raw/，把磁盘文件与数据库对齐。

    - 磁盘有、DB 无：新增记录（chunk_count 从 Chroma 查询）
    - 两边都有：更新 chunk_count、file_size
    - DB 有、磁盘无：标记删除（保留记录，避免误删）
    """
    from app.core.config import get_settings
    from app.rag.vectorstore import get_vectorstore
    from app.utils.file_utils import list_raw_files
    from app.utils.hash_utils import md5_file

    settings = get_settings()
    disk_files = {str(p): p for p in list_raw_files()}

    # 读现有 DB 记录
    result = await db.execute(select(DocumentModel))
    db_records = {r.file_path: r for r in result.scalars().all()}

    def _chunk_count(source: str) -> int:
        vs = get_vectorstore()
        try:
            data = vs.get(where={"source": source}, include=[])
            return len(data.get("ids", []) or [])
        except Exception:
            return 0

    added, updated, missing = 0, 0, 0

    for path_str, path in disk_files.items():
        if path_str in db_records:
            # 已存在：刷新 chunk_count 和 size
            rec = db_records[path_str]
            new_size = path.stat().st_size
            new_chunks = await asyncio.to_thread(_chunk_count, path_str)
            if rec.file_size != new_size or rec.chunk_count != new_chunks:
                rec.file_size = new_size
                rec.chunk_count = new_chunks
                updated += 1
        else:
            # 新文件：从 Chroma 查 chunk 数并插入记录
            file_md5 = await asyncio.to_thread(md5_file, path)
            chunk_count = await asyncio.to_thread(_chunk_count, path_str)
            db.add(DocumentModel(
                file_name=path.name,
                file_path=path_str,
                file_md5=file_md5,
                file_size=path.stat().st_size,
                file_type=path.suffix.lstrip("."),
                chunk_count=chunk_count,
            ))
            added += 1

    # DB 有但磁盘无：统计（不自动删除，交给用户手动处理）
    for path_str in db_records:
        if path_str not in disk_files:
            missing += 1

    await db.commit()
    logger.info(
        "同步完成 | 新增 %d | 更新 %d | 磁盘缺失 %d",
        added, updated, missing,
    )
    return {"added": added, "updated": updated, "missing": missing}
