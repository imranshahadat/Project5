"""Ingestion pipeline — updated to propagate document metadata into chunk metadata.

CHANGES from original:
  - chunk metadata now includes tenant_id, shared_groups, shared_subjects
    pulled from the Document row's metadata JSONB
  - this is what makes the access-control filter in retrieve_node actually match

Flow:
  upload -> S3 -> process_s3_key(key)
    CHECK DATABASE   (missing -> RETURN, ready -> RETURN)
    CHECK STATUS     (only pending/failed proceed)
    STATUS = PROCESSING
    DOWNLOAD FROM S3
    VALIDATE FILE    (pdf | docx | txt/md dispatch)
    EXTRACT TEXT     (PdfReader / python-docx / UTF-8)
    chunks(text)     (size + overlap from .env)
    GENERATE EMBEDDINGS (embed(part), batches of 64)
    CREATE VECTOR DATA  (ids "{doc_id}:{i}" + metadata WITH ACCESS TAGS)
    UPSERT INTO PINECONE (adapter batches at 100)
    STATUS = READY -> AUDIT DATABASE -> LOG SUCCESS
"""

import logging
from dataclasses import dataclass
from typing import Any, Optional

from app.application.dependencies.providers import (
    build_audit_repository,
    build_document_repository,
    get_db_session,
    get_embeddings,
    get_storage,
    get_vector_store,
)
from app.application.services.chunking import chunk_text
from app.core.config import get_settings
from app.core.exceptions import (
    DocumentNotFoundError,
    FileValidationError,
    TextExtractionError,
)
from app.domains.infrastructure.extractors.factory import (
    EXTRACTOR_REGISTRY,
    get_extractor,
)

log = logging.getLogger(__name__)

EMBED_BATCH = 64
MAX_FILE_BYTES = 25 * 1024 * 1024  # 25 MB upload guard
PROCEED_STATUSES = {"pending", "failed"}


@dataclass
class IngestionResult:
    doc_id: str
    status: str  # "ready" | "skipped"
    num_chunks: int = 0
    reason: Optional[str] = None


def process_s3_key(key: str) -> IngestionResult:
    """Entry point — call after a file lands in S3 at `key`."""
    settings = get_settings()

    # --- CHECK DATABASE ---------------------------------------------------
    doc = _lookup_document(key)
    if doc is None:
        log.info("No document row for %s — skipping", key)
        return IngestionResult(
            doc_id="", status="skipped", reason="document row missing"
        )
    doc_id = doc["id"]

    # --- CHECK STATUS: only pending/failed proceed --------------------------
    if doc["status"] not in PROCEED_STATUSES:
        log.info("Document %s is '%s' — nothing to do", doc_id, doc["status"])
        return IngestionResult(
            doc_id=doc_id, status="skipped", reason=f"status={doc['status']}"
        )

    # --- STATUS = PROCESSING --------------------------------------------------
    _set_status(doc_id, "processing")
    log.info("Ingesting '%s' from %s", doc["title"], key)

    try:
        # --- DOWNLOAD FROM S3 ------------------------------------------------
        data = get_storage().get(key)

        # --- VALIDATE FILE ------------------------------------------------------
        _validate_file(data, key)

        # --- EXTRACT TEXT ------------------------------------------------------
        text = get_extractor(key).extract(data, key)
        if not text.strip():
            raise TextExtractionError(
                "Extracted no text — empty file or scanned PDF without a text layer"
            )

        # --- chunks(text) -------------------------------------------------------
        chunks = chunk_text(
            text, size=settings.chunk.size, overlap=settings.chunk.overlap
        )
        if not chunks:
            raise TextExtractionError("Chunking produced 0 chunks")
        log.info("Extracted %d chars -> %d chunks", len(text), len(chunks))

        # --- GENERATE EMBEDDINGS (batched) ------------------------------------------
        vectors = _embed_in_batches(chunks)

        # --- CREATE VECTOR DATA (with access-control metadata) -----------------
        # Pull access tags from the document's metadata so the retrieve node's
        # access filter can match them.
        doc_meta = doc.get("metadata") or {}
        tenant_id = doc_meta.get("tenant_id", "public")
        shared_groups = doc_meta.get("shared_groups", [])
        shared_subjects = doc_meta.get("shared_subjects", [])
        tags = doc_meta.get("tags", [])

        ids = [f"{doc_id}:{i}" for i in range(len(chunks))]
        metadatas = [
            {
                "doc_id": doc_id,
                "chunk_index": i,
                "title": doc["title"],
                "text": chunk,
                # access-control fields — match the TenantAccessFilterBuilder
                "tenant_id": tenant_id,
                "shared_groups": shared_groups,
                "shared_subjects": shared_subjects,
                # searchable tags for future hybrid filtering
                "tags": tags,
            }
            for i, chunk in enumerate(chunks)
        ]

        # --- UPSERT INTO PINECONE (adapter batches at 100) --------------------------
        store = get_vector_store()
        store.delete_by_filter({"doc_id": {"$eq": doc_id}})  # idempotent re-ingest
        store.upsert(ids=ids, vectors=vectors, metadatas=metadatas)

        # --- STATUS = READY -> AUDIT -> LOG SUCCESS -------------------------------
        _set_status(doc_id, "ready")
        _audit(
            "document.ingested",
            doc_id,
            {"chunks": len(chunks), "source": key, "tenant_id": tenant_id},
        )
        log.info("Ingestion complete: %s (%d vectors, tenant=%s)", doc_id, len(chunks), tenant_id)
        return IngestionResult(doc_id=doc_id, status="ready", num_chunks=len(chunks))

    except Exception as e:
        # --- ERROR HANDLING: log -> STATUS=failed -> AUDIT -> RAISE --------------
        log.exception("Ingestion failed for %s", doc_id)
        _set_status(doc_id, "failed")
        _audit("document.ingest_failed", doc_id, {"source": key, "error": str(e)[:500]})
        raise


# ---- helpers ---------------------------------------------


def _lookup_document(key: str) -> Optional[dict]:
    with get_db_session() as session:
        return build_document_repository(session).find_by_source(key)


def _set_status(doc_id: str, status: str) -> None:
    with get_db_session() as session:
        build_document_repository(session).update_status(doc_id, status)


def _validate_file(data: bytes, key: str) -> None:
    if not data:
        raise FileValidationError(f"Empty file: {key}")
    if len(data) > MAX_FILE_BYTES:
        raise FileValidationError(f"File too large ({len(data)} bytes): {key}")
    ext = key.rsplit(".", 1)[-1].lower() if "." in key else ""
    if ext not in EXTRACTOR_REGISTRY:
        raise FileValidationError(
            f"Unsupported file type '.{ext}'. Supported: {', '.join(EXTRACTOR_REGISTRY)}"
        )


def _embed_in_batches(texts: list[str]) -> list[list[float]]:
    embeddings = get_embeddings()
    out: list[list[float]] = []
    for i in range(0, len(texts), EMBED_BATCH):
        out.extend(embeddings.embed_documents(texts[i : i + EMBED_BATCH]))
    return out


def _audit(action: str, doc_id: str, detail: dict) -> None:
    with get_db_session() as session:
        build_audit_repository(session).append(action, "document", doc_id, detail)


def ingest_document(doc_id: str) -> IngestionResult:
    """Back-compat wrapper: resolve the row's source key, then process it."""
    with get_db_session() as session:
        doc = build_document_repository(session).get(doc_id)
    if doc is None or not doc.get("source"):
        raise DocumentNotFoundError(f"Document '{doc_id}' not found or has no S3 key")
    return process_s3_key(doc["source"])
