"""POST /documents/upload + GET /documents + GET /documents/{id}
   DELETE /documents/{id} + POST /documents/{id}/reingest

Upload flow:
  1. validate file (size + extension)
  2. stream file to temp disk (prevents OOM)
  3. create Document row (status=pending)
  4. upload to S3 at documents/{doc_id}/{filename}
  5. enqueue ARQ background task for ingestion
  6. set source on the row
  7. return immediately
"""

import hashlib
import logging
import tempfile
from pathlib import Path
from typing import Any, Optional

from arq import ArqRedis
from arq.connections import RedisSettings, create_pool
from fastapi import (
    APIRouter,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import delete

from app.api.deps import PrincipalDep
from app.api.v1.schemas import (
    DocumentDetail,
    DocumentListResponse,
    DocumentUploadResponse,
)
from app.application.dependencies.providers import (
    build_document_repository,
    get_db_session,
    get_storage,
)
from app.application.services.ingestion import MAX_FILE_BYTES
from app.domains.infrastructure.database.models import Document
from app.domains.infrastructure.extractors.factory import EXTRACTOR_REGISTRY

log = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])
limiter = Limiter(key_func=get_remote_address)
arq_pool: ArqRedis | None = None


async def get_arq_pool() -> ArqRedis:
    """Get or create ARQ connection pool."""
    global arq_pool
    if arq_pool is None:
        arq_pool = await create_pool(RedisSettings())
    return arq_pool


def _allowed(filename: str) -> bool:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in EXTRACTOR_REGISTRY


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    summary="Upload a document",
)
@limiter.limit("5/minute")
async def upload_document(
    request: Request,
    principal: PrincipalDep,
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    tenant_id: str = Form("public"),
    tags: str = Form(""),
    description: str = Form(""),
    author: str = Form(""),
) -> DocumentUploadResponse:
    """Upload a document using streaming to prevent OOM and ARQ for persistence."""

    filename = file.filename or "untitled"
    if not _allowed(filename):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(EXTRACTOR_REGISTRY)}",
        )

    title = title or filename
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]

    # CRITICAL FIX: Stream file to temp file instead of loading into memory
    temp_file_path = None
    file_hash = hashlib.sha256()
    total_size = 0

    try:
        # Create temp file
        temp_file = tempfile.NamedTemporaryFile(
            delete=False, suffix=Path(filename).suffix
        )
        temp_file_path = temp_file.name

        # Stream file in 1MB chunks
        chunk_size = 1024 * 1024
        while chunk := await file.read(chunk_size):
            temp_file.write(chunk)
            file_hash.update(chunk)
            total_size += len(chunk)

            # Check size limit during streaming
            if total_size > MAX_FILE_BYTES:
                temp_file.close()
                Path(temp_file_path).unlink(missing_ok=True)
                raise HTTPException(
                    status_code=413,
                    detail=f"File too large ({total_size} bytes). Max: {MAX_FILE_BYTES} bytes.",
                )

        temp_file.close()

        # Check if file is empty
        if total_size == 0:
            Path(temp_file_path).unlink(missing_ok=True)
            raise HTTPException(status_code=400, detail="Empty file.")

        file_hash_hex = file_hash.hexdigest()

        metadata: dict[str, Any] = {
            "tenant_id": tenant_id,
            "tags": tag_list,
            "description": description or None,
            "author": author or None,
            "filename": filename,
            "content_type": file.content_type,
            "file_hash": file_hash_hex,
        }

        # Async database session
        async with get_db_session() as session:
            repo = build_document_repository(session)

            existing_doc = await repo.find_by_file_hash(
                file_hash=file_hash_hex,
                tenant_id=tenant_id,
            )
            if existing_doc:
                Path(temp_file_path).unlink(missing_ok=True)
                raise HTTPException(
                    status_code=409,
                    detail=f"Document with identical content already exists (ID: {existing_doc['id']})",
                )

            doc_id = await repo.add(
                title=title,
                content="",
                source=None,
                metadata=metadata,
            )

        s3_key = f"documents/{doc_id}/{filename}"

        # Upload to S3 from temp file
        try:
            storage = get_storage()
            with open(temp_file_path, "rb") as f:
                storage.put(
                    s3_key,
                    f,
                    content_type=file.content_type or "application/octet-stream",
                )
        except Exception as e:
            log.exception("S3 upload failed for %s", s3_key)
            async with get_db_session() as session:
                repo = build_document_repository(session)
                await repo.update_status(
                    doc_id, "failed", error_message=f"S3 upload failed: {e}"
                )
            raise HTTPException(status_code=502, detail=f"Storage upload failed: {e}")

        # Enqueue ARQ job for ingestion (AFTER S3 upload is complete)
        try:
            pool = await get_arq_pool()
            job = await pool.enqueue_job("process_document_task", s3_key)
            log.info(f"Enqueued ARQ job {job.job_id} for {s3_key}")
        except Exception as e:
            log.exception(f"Failed to enqueue ARQ job for {s3_key}: {e}")
            async with get_db_session() as session:
                repo = build_document_repository(session)
                await repo.update_status(
                    doc_id, "failed", error_message="Failed to queue ingestion task"
                )
            raise HTTPException(
                status_code=500, detail="Failed to queue document processing"
            )

        # Link S3 key to Document row
        async with get_db_session() as session:
            repo = build_document_repository(session)
            await repo.set_source(doc_id, s3_key)

        log.info(
            "uploaded %s -> s3_key=%s doc_id=%s hash=%s",
            filename,
            s3_key,
            doc_id,
            file_hash_hex,
        )

        return DocumentUploadResponse(
            doc_id=doc_id,
            title=title,
            status="pending",
            source=f"s3://{s3_key}",
            metadata=metadata,
            message="Document uploaded. Ingestion queued.",
        )

    finally:
        # Always clean up temp file, even if an error occurred
        if temp_file_path and Path(temp_file_path).exists():
            try:
                Path(temp_file_path).unlink()
            except Exception as e:
                log.warning(f"Failed to clean up temp file {temp_file_path}: {e}")


@router.get("", response_model=DocumentListResponse, summary="List documents")
async def list_documents(
    request: Request,
    principal: PrincipalDep,
    limit: int = 50,
) -> DocumentListResponse:
    async with get_db_session() as session:
        repo = build_document_repository(session)
        docs = await repo.list(limit=limit)
    return DocumentListResponse(documents=docs, total=len(docs))


@router.get("/{doc_id}", response_model=DocumentDetail, summary="Get document details")
async def get_document(
    request: Request,
    principal: PrincipalDep,
    doc_id: str,
) -> DocumentDetail:
    async with get_db_session() as session:
        repo = build_document_repository(session)
        doc = await repo.get(doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found")
    return DocumentDetail(**doc)


@router.delete("/{doc_id}", summary="Delete a document")
async def delete_document(
    request: Request,
    principal: PrincipalDep,
    doc_id: str,
) -> dict:
    async with get_db_session() as session:
        repo = build_document_repository(session)
        doc = await repo.get(doc_id)
        if doc is None:
            raise HTTPException(
                status_code=404, detail=f"Document '{doc_id}' not found"
            )

        source = doc.get("source")

        # delete from vector store
        try:
            from app.application.dependencies.providers import get_vector_store

            get_vector_store().delete_by_filter({"doc_id": {"$eq": doc_id}})
        except Exception as e:
            log.warning("vector store delete failed for %s: %s", doc_id, e)

        # delete from S3
        if source:
            try:
                get_storage().delete(source)
            except Exception as e:
                log.warning("S3 delete failed for %s: %s", source, e)

        # delete from DB (Async SQLAlchemy)
        await session.execute(delete(Document).where(Document.id == doc_id))
        await session.flush()

    return {"doc_id": doc_id, "deleted": True}


@router.post("/{doc_id}/reingest", summary="Re-trigger ingestion")
async def reingest_document(
    request: Request,
    principal: PrincipalDep,
    doc_id: str,
) -> dict:
    async with get_db_session() as session:
        repo = build_document_repository(session)
        doc = await repo.get(doc_id)
        if doc is None:
            raise HTTPException(
                status_code=404, detail=f"Document '{doc_id}' not found"
            )
        if not doc.get("source"):
            raise HTTPException(status_code=400, detail="Document has no source file")

        await repo.update_status(doc_id, "pending")

    # Enqueue ARQ job for re-ingestion
    try:
        pool = await get_arq_pool()
        job = await pool.enqueue_job("process_document_task", doc["source"])
        log.info(f"Enqueued ARQ re-ingestion job {job.job_id} for {doc['source']}")
    except Exception as e:
        log.exception(f"Failed to enqueue ARQ re-ingestion job: {e}")
        raise HTTPException(status_code=500, detail="Failed to queue re-ingestion task")

    return {"doc_id": doc_id, "status": "pending", "message": "Re-ingestion queued."}
