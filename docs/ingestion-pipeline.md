# Ingestion Pipeline — S3 → pypdf → Chunks → Vercel Embeddings → Pinecone → Postgres

> Project4 milestone: turn a stored file into searchable vectors, tracking
> status in PostgreSQL. Built on the same ports-and-adapters architecture.

## Flow

    S3  documents/{doc_id}/{filename}
     │  get_storage().get(key)
     ▼
    extract   — dispatched by extension: .pdf → pypdf, .txt/.md → plain text
     ▼
    chunk_text(size=500, overlap=50)     # CHUNK_SIZE / CHUNK_OVERLAP from .env
     ▼
    embed     — Vercel Gateway · cohere/embed-v4.0 · batches of 64 (EMBED_BATCH)
     ▼
    Pinecone  upsert ids="{doc_id}:{i}"
              metadata = {doc_id, chunk_index, title, text}
     ▼
    Postgres  documents.status: pending → processing → ready | failed

## Files

| Layer      | File                                                            | Purpose |
|------------|------------------------------------------------------------------|---------|
| Service    | `src/app/application/services/ingestion.py`                      | Orchestrates the whole pipeline |
| Domain     | `src/app/application/services/chunking.py`                       | Sliding-window chunker (pure logic) |
| Port       | `src/app/domains/interfaces/extractor.py`                        | `BaseTextExtractor` |
| Adapter    | `src/app/domains/infrastructure/extractors/pypdf.py`             | PDF → text (pypdf) |
| Adapter    | `src/app/domains/infrastructure/extractors/plain_text.py`        | UTF-8 text → text |
| Factory    | `src/app/domains/infrastructure/extractors/factory.py`           | Extension → extractor registry |
| Port       | `src/app/domains/interfaces/repositories.py`                     | + `update_status`, `set_source` |
| Adapter    | `src/app/domains/infrastructure/database/postgres_repositories.py` | Implements the new methods |
| Script     | `scripts/smoke_ingestion.py`                                     | End-to-end smoke test |
| Script     | `scripts/create_pinecone_index.py`                               | Classic-index bootstrap + write probe |

## Status lifecycle (documents.status)

    pending ──► processing ──► ready
                    │
                    └──► failed   (reason logged; doc can be re-ingested)

Each transition runs in its **own short transaction** (`get_db_session()`), so
`processing` and `failed` survive pipeline crashes — one long transaction would
roll the status back together with the error.

## Key design decisions

1. **Row before upload.** The S3 key contains the document id, so the row is
   created first, the real id is used in the key, then `set_source()` records it:
   `add() → storage.put(f"documents/{id}/{filename}") → set_source(id, key)`.
   (Skipping this ordering caused `DocumentNotFoundError` during development.)
2. **Deterministic vector ids** `{doc_id}:{chunk_index}` + `delete_by_filter`
   before upsert → re-ingestion is idempotent, no stale/duplicate chunks.
3. **Batched embeddings** — `embed_documents` is called in batches of 64 to
   stay within provider limits.
4. **Chunk text lives in Pinecone metadata** (`text` field) so retrieval needs
   only one lookup; Postgres `content` stays a placeholder for now.
5. **Extractor dispatch by extension** of the S3 key — mirrors the provider
   factory pattern; unknown extensions raise `UnsupportedFileTypeError`.

## Runbook

    # full end-to-end smoke test (creates its own row + file)
    python scripts/smoke_ingestion.py

    # ingest a real PDF
    python scripts/smoke_ingestion.py /path/to/file.pdf

    # re-ingest a document that is stuck in 'failed'
    python -c "import sys; sys.path.insert(0,'src'); \
               import logging; logging.basicConfig(level=logging.INFO); \
               from app.application.services.ingestion import ingest_document; \
               print(ingest_document('<doc_id>'))"

    # inspect recent rows
    python -c "import sys; sys.path.insert(0,'src'); \
               from app.application.dependencies.providers import get_db_session, build_document_repository; \
               [print(d['id'], d['status'], d['source']) \
                for d in build_document_repository(get_db_session().__enter__()).list(5) ]"

## Troubleshooting (issues actually hit while building this)

1. **`DocumentNotFoundError` right after creating a row** — the script used a
   self-generated uuid for lookup while the repository generated its own id.
   Always use the id **returned** by `add()`.
2. **`[400] This index has a document schema ...`** — the Pinecone index was
   created via the document/integrated-embedding flow. Classic indexes only:
   delete it, recreate with `scripts/create_pinecone_index.py` (it probe-writes
   to verify), then update `PINECONE_INDEX_HOST`. A classic host contains
   `svc.<region>.aws.pinecone.io`.
3. **Scanned PDFs** — no text layer → `TextExtractionError`, status `failed`.
   OCR (pytesseract) is a future enhancement.
4. **`IndentationError` in the repository** — class methods sit at 4 spaces;
   a method accidentally nested inside another breaks the import.

## Next steps

- Retrieval service: embed query → Pinecone `query(top_k, filter)` → optional
  rerank → LLM answer with citations
- Upload API endpoint (FastAPI): multipart upload → row → S3 → background ingest
- Write extracted text back into `documents.content`
