
```markdown
# Vector Store (Pinecone) & Object Storage (AWS S3)

> Project4 — Infrastructure layer extension: vendor-neutral vector database and
> object storage, wired into the hexagonal architecture (ports & adapters).

## Overview

This module adds two new integrations, following the same pattern as the LLM and
embeddings providers:

| Layer          | File                                                              | Purpose |
|----------------|-------------------------------------------------------------------|---------|
| Port           | `src/app/domains/interfaces/vector_store.py`                      | `BaseVectorStore` ABC — any vector DB |
| Port           | `src/app/domains/interfaces/storage.py`                           | `BaseStorage` ABC — any object store |
| Adapter        | `src/app/domains/infrastructure/vector_store/pinecone.py`         | Pinecone serverless (classic vectors API) |
| Adapter        | `src/app/domains/infrastructure/storage/s3.py`                    | AWS S3 via boto3 |
| Factory        | `src/app/domains/infrastructure/vector_store/factory.py`          | Registry + shared `build_provider()` |
| Factory        | `src/app/domains/infrastructure/storage/factory.py`               | Registry + shared `build_provider()` |
| Composition    | `src/app/application/dependencies/providers.py`                   | `get_vector_store()`, `get_storage()` (cached) |
| Config         | `src/app/core/config.py`                                          | `vector_store_provider`, `storage_provider`, Pinecone/S3 settings |
| Errors         | `src/app/core/exceptions.py`                                      | `StorageError`, `StorageProviderError` |
| Scripts        | `scripts/create_pinecone_index.py`, `scripts/smoke_vector_and_s3.py` | Index bootstrap + end-to-end smoke test |

## Architecture

    app/application/dependencies/providers.py   (composition root, lru_cache)
            │
    ┌───────┴────────────────────────────────┐
    ▼                                        ▼
    infrastructure/vector_store/pinecone.py   infrastructure/storage/s3.py
    ▼                                        ▼
    interfaces/vector_store.py (port)         interfaces/storage.py (port)
    ▼                                        ▼
    Pinecone index                            S3 bucket

**Ingestion flow (next milestone):**

    raw file ──► S3 (documents/{doc_id}/source.ext)
             ──► chunk (CHUNK_SIZE / CHUNK_OVERLAP)
             ──► embed (Vercel Gateway · cohere/embed-v4.0 · 1024 dims)
             ──► Pinecone upsert (metadata: doc_id, chunk_index, text)
             ──► Postgres documents.status = "ready"

**Retrieval flow:**

    query ──► embed_query ──► Pinecone query(top_k) ──► rerank (optional) ──► LLM

## Ports (vendor-neutral contracts)

### BaseVectorStore

    upsert(ids, vectors, metadatas) -> int       # batched write
    query(vector, top_k=4, filter=None) -> list  # [{'id', 'score', 'metadata'}]
    delete_by_filter(filter) -> None             # e.g. {"doc_id": {"$eq": doc_id}}
    stats() -> dict                              # health/debug probe

### BaseStorage

    put(key, data, content_type) -> str          # returns s3://bucket/key
    get(key) -> bytes                            # raises StorageError if missing
    delete(key) -> None
    presigned_url(key, expires_in=None) -> str   # temporary GET link

## Adapters

### PineconeVectorStore
- Connects by `PINECONE_INDEX_HOST` (serverless indexes are host-addressed;
  `PINECONE_ENVIRONMENT` is legacy and unused).
- Batches upserts at 100 vectors/batch (safe for 1024-dim vectors + metadata).
- Optional `PINECONE_NAMESPACE`; empty = default namespace.
- `delete_by_filter` requires a serverless index (classic dense is fine).

### S3Storage
- Uses sigv4 presigned URLs (`botocore Config(signature_version="s3v4")`).
- Bucket required (`AWS_S3_BUCKET_NAME`); credentials optional — falls back to
  boto3's default chain (env vars / IAM role) when not set in `.env`.
- Key naming convention: `documents/{doc_id}/source.ext`, `smoke/…` for tests.

## Configuration reference (.env)

    # Vector store (Pinecone serverless)
    VECTOR_STORE_PROVIDER="pinecone"
    PINECONE_API_KEY="pcsk_..."
    PINECONE_INDEX_HOST="https://rag-knowledge-base-<suffix>.svc.ap-southeast-1.aws.pinecone.io"
    PINECONE_NAMESPACE=""              # optional
    PINECONE_REGION="ap-southeast-1"   # must match the index's region
    PINECONE_DIMENSION=1024            # must match cohere/embed-v4.0

    # Object storage (S3)
    STORAGE_PROVIDER="aws"
    AWS_ACCESS_KEY_ID="..."
    AWS_SECRET_ACCESS_KEY="..."
    AWS_REGION="ap-south-1"            # must match the bucket's region
    AWS_S3_BUCKET_NAME="imranali-..."
    S3_PRESIGN_EXPIRY=3600

New fields in `AppSettings`: `vector_store_provider` (default `pinecone`),
`storage_provider` (default `aws`), `PineconeSettings.namespace`,
`AWSSettings.presign_expiry`.

## Setup

    pip install pinecone boto3

Create the index (classic dense vectors index — see Troubleshooting #3):

    python scripts/create_pinecone_index.py

Then copy the printed **host** into `PINECONE_INDEX_HOST` in `.env`.
Recreating an index changes its host — always update this value.

## Smoke test

    python scripts/smoke_vector_and_s3.py

Expected output:

    S3 OK: s3://<bucket>/smoke/test-<ts>.txt
    Presigned: https://<bucket>.s3.amazonaws.com/smoke/test-<ts>.txt ...
    S3 cleaned up
    Vector store stats: {'dimension': 1024, 'metric': 'cosine', 'total_vector_count': 0, ...}
    Query hits: [('smoke-0001', ~1.0)]
    Pinecone cleaned up

A self-query scores ≈ 1.0 (cosine of a vector with itself).

## Troubleshooting (issues actually hit while building this)

1. **`NameError: name 'BaseStorage' is not defined`**
   The adapter file was missing `from app.domains.interfaces.storage import BaseStorage`.
   Ports live in `src/app/domains/interfaces/*.py` — every adapter imports its port.

2. **`host 'rag-knowledge-base' does not appear to be a valid URL`**
   `PINECONE_INDEX_HOST` must be the **full URL** from the Pinecone console, not
   just the index name. Also note: shell-exported env vars override `.env` in
   pydantic-settings (`echo $PINECONE_INDEX_HOST` to check; `unset` if stale).

3. **`[400] This index has a document schema, so writes must go through the documents API`**
   The index was created via the console's integrated-embedding flow. That index
   type only accepts Pinecone's server-side embedding via the new Documents API
   (no Python SDK support yet) and blocks the classic vectors API.
   **Fix:** delete the index and recreate a classic dense index with
   `scripts/create_pinecone_index.py` (dim 1024, cosine, serverless), then update
   `PINECONE_INDEX_HOST`. This keeps embeddings client-side via the
   `BaseEmbeddings` port (Vercel Gateway / cohere embed-v4.0).

4. **Region mismatch**
   `PINECONE_REGION` must match the index's actual region (the host URL shows it),
   and `AWS_REGION` must match the S3 bucket's region.

## Next steps

- Ingestion service: S3 upload → chunk → embed → upsert → Postgres row `ready`
- Retrieval service: embed query → Pinecone `query(top_k)` → optional reranker → LLM
- Wire `reset_all_caches()` into tests between provider-dependent cases
```

## 2. Create the file and commit

```bash
cd ~/Documents/YoutubeProject/Project4
mkdir -p docs
nano docs/vector-store-and-s3.md     # paste the doc above, save
```

```bash
# Stage everything from this milestone
git add docs/vector-store-and-s3.md \
        scripts/create_pinecone_index.py \
        scripts/smoke_vector_and_s3.py \
        src/app/domains/interfaces/vector_store.py \
        src/app/domains/interfaces/storage.py \
        src/app/domains/infrastructure/vector_store/ \
        src/app/domains/infrastructure/storage/ \
        src/app/core/config.py \
        src/app/core/exceptions.py \
        src/app/application/dependencies/providers.py

# Safety check — make sure .env / .env2 are NOT staged
git status
git check-ignore .env && echo ".env ignored ✔"

git commit -m "feat(infra): add Pinecone vector store and AWS S3 storage adapters" -m "
- Add vendor-neutral ports: BaseVectorStore, BaseStorage
- Add adapters: PineconeVectorStore (batched upsert, host-addressed serverless)
  and S3Storage (boto3, sigv4 presigned URLs)
- Add provider factories reusing the shared _builder pattern
- Extend settings: vector_store_provider, storage_provider, PINECONE_NAMESPACE,
  S3_PRESIGN_EXPIRY
- Extend exceptions: StorageError, StorageProviderError
- Wire get_vector_store()/get_storage() into the composition root
- Add smoke test (S3 + Pinecone roundtrips) and classic-index creation script
- Add docs/vector-store-and-s3.md with config reference and troubleshooting
"

git log --oneline -1
```