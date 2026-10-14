"""文档管理接口（仅 admin）。"""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.core.logging import get_logger
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.document import DocumentItem, UploadResponse
from app.services import document_service
from app.utils.file_utils import is_supported


router = APIRouter(prefix="/documents", tags=["documents"])
logger = get_logger(__name__)


@router.post("", response_model=UploadResponse)
async def upload(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_admin),
) -> UploadResponse:
    if not is_supported(file.filename or ""):
        raise HTTPException(400, f"不支持的文件类型：{file.filename}")

    content = await file.read()
    record, skipped = await document_service.upload_and_index(
        db, file.filename, content,
    )
    return UploadResponse(
        document_id=record.id,
        file_name=record.file_name,
        chunk_count=record.chunk_count,
        skipped=skipped,
    )


@router.get("", response_model=list[DocumentItem])
async def list_docs(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_admin),
) -> list[DocumentItem]:
    records = await document_service.list_documents(db)
    return [
        DocumentItem(
            id=r.id, file_name=r.file_name, file_size=r.file_size,
            chunk_count=r.chunk_count, created_at=r.created_at.isoformat(),
        )
        for r in records
    ]


@router.post("/sync")
async def sync_documents(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_admin),
) -> dict:
    """扫描 data/raw/ 并同步到数据库。"""
    result = await document_service.sync_from_disk(db)
    return {"code": 0, "message": "synced", "data": result}


@router.delete("/{doc_id:int}")
async def delete_doc(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_admin),
) -> dict:
    ok = await document_service.delete_document(db, doc_id)
    if not ok:
        raise HTTPException(404, "文档不存在")
    return {"code": 0, "message": "deleted"}