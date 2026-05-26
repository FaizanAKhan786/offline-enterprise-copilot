"""
Document management routes: upload, list, delete.
"""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_permission
from app.core.config import get_settings
from app.core.security import TokenPayload
from app.db.session import get_db
from app.models.models import Document
from app.schemas.schemas import DocumentListResponse, DocumentResponse
from app.services.rag.processor import document_processor
from app.services.rag.retrieval import retrieval_engine

router = APIRouter(prefix="/documents", tags=["Documents"])
settings = get_settings()

ALLOWED_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "image/png",
    "image/jpeg",
    "image/tiff",
}


@router.post("/upload", response_model=DocumentResponse, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(require_permission("documents:write")),
):
    """Upload and process a document for RAG indexing."""
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, f"Unsupported file type: {file.content_type}")

    if file.size and file.size > settings.max_upload_size_mb * 1024 * 1024:
        raise HTTPException(400, f"File too large. Max: {settings.max_upload_size_mb}MB")

    # Save file
    doc_id = uuid.uuid4()
    upload_dir = settings.upload_dir / str(user.sub)
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / f"{doc_id}_{file.filename}"

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Create DB record
    doc = Document(
        id=doc_id,
        owner_id=uuid.UUID(user.sub),
        filename=file.filename or "unnamed",
        content_type=file.content_type or "application/octet-stream",
        file_size=file.size or file_path.stat().st_size,
        file_path=str(file_path),
        status="processing",
    )
    db.add(doc)
    await db.flush()

    # Process and index (inline for now; move to Celery for production)
    try:
        chunks = await document_processor.process(
            file_path=file_path,
            content_type=doc.content_type,
            document_id=str(doc_id),
            filename=doc.filename,
        )
        indexed = await retrieval_engine.index_chunks(chunks, str(doc_id))
        doc.status = "ready"
        doc.chunk_count = indexed
    except Exception as e:
        doc.status = "error"
        doc.metadata_ = {"error": str(e)}

    await db.flush()
    await db.refresh(doc)
    return DocumentResponse.model_validate(doc)


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(require_permission("documents:read")),
):
    result = await db.execute(
        select(Document)
        .where(Document.owner_id == uuid.UUID(user.sub))
        .order_by(Document.created_at.desc())
    )
    docs = result.scalars().all()
    return DocumentListResponse(
        documents=[DocumentResponse.model_validate(d) for d in docs],
        total=len(docs),
    )


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(require_permission("documents:delete")),
):
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")

    # Remove from vector store
    await retrieval_engine.delete_document(str(document_id))

    # Remove file
    Path(doc.file_path).unlink(missing_ok=True)

    await db.delete(doc)
    await db.flush()
