"""POST /documents/upload  +  GET /documents  +  GET /documents/{id}
   DELETE /documents/{id}  +  POST /documents/{id}/reingest

Upload flow:
  1. validate file (size + extension)
  2. create Document row (status=pending, source=None)
  3. upload to S3 at documents/{doc_id}/{filename}
  4. set source on the row
  5. return immediately — ingestion runs in a BackgroundTask (thread pool)

Metadata (tenant_id, tags, description, author) is stored as JSONB on the
Document row AND propagated into chunk metadata by the ingestion pipeline,
which is what makes the access-control filter actually match.
"""

import hashlib
import logging
import os
from typing import Any, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    Form,
    HTTPException,
    UploadFile,
)

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
from app.application.services.ingestion import MAX_FILE_BYTES, process_s3_key
from app.core.exceptions import FileValidationError, StorageError
from app.domains.infrastructure.extractors.factory import EXTRACTOR_REGISTRY

log = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


def _allowed(filename: str) -> bool:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in EXTRACTOR_REGISTRY


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    summary="Upload a document",
)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    tenant_id: str = Form("public"),
    tags: str = Form(""),
    description: str = Form(""),
    author: str = Form(""),
) -> DocumentUploadResponse:
    """Upload a document and trigger background ingestion.

    Rejects duplicate files using their SHA-256 content hash.
    """

    # ---- Validate filename and extension ----
    filename = file.filename or "untitled"

    if not _allowed(filename):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(EXTRACTOR_REGISTRY)}",
        )

    # ---- Read and validate file ----
    data = await file.read()

    if not data:
        raise HTTPException(status_code=400, detail="Empty file.")

    if len(data) > MAX_FILE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({len(data)} bytes). Max: {MAX_FILE_BYTES} bytes.",
        )

    # ---- Compute SHA-256 hash ----
    file_hash = hashlib.sha256(data).hexdigest()

    # ---- Check for duplicate documents ----
    title = title or filename
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]

    with get_db_session() as session:
        repo = build_document_repository(session)

        existing_doc = repo.find_by_file_hash(
            file_hash=file_hash,
            tenant_id=tenant_id,
        )

        if existing_doc:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Document with identical content already exists "
                    f"(ID: {existing_doc['id']}, "
                    f"Title: {existing_doc['title']})."
                ),
            )

    # ---- Prepare metadata ----
    metadata: dict[str, Any] = {
        "tenant_id": tenant_id,
        "tags": tag_list,
        "description": description or None,
        "author": author or None,
        "filename": filename,
        "content_type": file.content_type,
        "file_hash": file_hash,
    }

    # ---- Create Document row ----
    with get_db_session() as session:
        repo = build_document_repository(session)

        doc_id = repo.add(
            title=title,
            content="",
            source=None,
            metadata=metadata,
        )

    # ---- Upload to S3 ----
    s3_key = f"documents/{doc_id}/{filename}"

    try:
        storage = get_storage()
        storage.put(
            s3_key,
            data,
            content_type=file.content_type or "application/octet-stream",
        )
    except Exception as e:
        log.exception("S3 upload failed for %s", s3_key)
        raise HTTPException(
            status_code=502,
            detail=f"Storage upload failed: {e}",
        )

    # ---- Link S3 key to Document row ----
    with get_db_session() as session:
        repo = build_document_repository(session)
        repo.set_source(doc_id, s3_key)

    log.info(
        "uploaded %s -> s3_key=%s doc_id=%s hash=%s",
        filename,
        s3_key,
        doc_id,
        file_hash,
    )

    # ---- Schedule background ingestion ----
    background_tasks.add_task(process_s3_key, s3_key)

    return DocumentUploadResponse(
        doc_id=doc_id,
        title=title,
        status="pending",
        source=f"s3://{s3_key}",
        metadata=metadata,
        message="Document uploaded. Ingestion started in background.",
    )


@router.get("", response_model=DocumentListResponse, summary="List documents")
async def list_documents(limit: int = 50) -> DocumentListResponse:
    """List documents with their ingestion status."""
    with get_db_session() as session:
        repo = build_document_repository(session)
        docs = repo.list(limit=limit)
    return DocumentListResponse(
        documents=docs,
        total=len(docs),
    )


@router.get("/{doc_id}", response_model=DocumentDetail, summary="Get document details")
async def get_document(doc_id: str) -> DocumentDetail:
    """Get one document's metadata + ingestion status."""
    with get_db_session() as session:
        repo = build_document_repository(session)
        doc = repo.get(doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found")
    return DocumentDetail(**doc)


@router.delete("/{doc_id}", summary="Delete a document")
async def delete_document(doc_id: str) -> dict:
    """Delete from Pinecone (chunks) + S3 (file) + Postgres (row)."""
    with get_db_session() as session:
        repo = build_document_repository(session)
        doc = repo.get(doc_id)
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

        # delete from DB — we need a raw delete since the repo doesn't have one
        from app.domains.infrastructure.database.models import Document

        session.query(Document).filter(Document.id == doc_id).delete()
        session.flush()

    return {"doc_id": doc_id, "deleted": True}


@router.post("/{doc_id}/reingest", summary="Re-trigger ingestion")
async def reingest_document(
    doc_id: str,
    background_tasks: BackgroundTasks,
) -> dict:
    """Set status back to pending and re-run ingestion."""
    with get_db_session() as session:
        repo = build_document_repository(session)
        doc = repo.get(doc_id)
        if doc is None:
            raise HTTPException(
                status_code=404, detail=f"Document '{doc_id}' not found"
            )
        if not doc.get("source"):
            raise HTTPException(status_code=400, detail="Document has no source file")
        repo.update_status(doc_id, "pending")

    background_tasks.add_task(process_s3_key, doc["source"])
    return {"doc_id": doc_id, "status": "pending", "message": "Re-ingestion started."}
