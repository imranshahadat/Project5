"""End-to-end ingestion smoke test.

Usage:
    python scripts/smoke_ingestion.py                     # inline sample .txt
    python scripts/smoke_ingestion.py /path/to/file.pdf   # a real PDF of yours
"""

import logging
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

from app.application.dependencies.providers import (  # noqa: E402
    build_document_repository,
    get_db_session,
    get_embeddings,
    get_storage,
    get_vector_store,
)
from app.application.services.ingestion import ingest_document  # noqa: E402

SAMPLE = "Vector ingestion smoke test. Imran is building a RAG pipeline. " * 30


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if path:
        data, filename, title = path.read_bytes(), path.name, path.stem
    else:
        data, filename, title = (
            SAMPLE.encode("utf-8"),
            "sample.txt",
            "Ingestion smoke test",
        )

    doc_id = str(uuid.uuid4())
    key = f"documents/{doc_id}/{filename}"

    # 1) upload raw file + create DB row (what the future upload API endpoint does)
    get_storage().put(key, data)
    # 1) create the DB row first (status=pending, no source yet)
    with get_db_session() as session:
        doc_id = build_document_repository(session).add(
            title, content="(raw file stored in S3)"
        )

    # 2) upload to S3 using the REAL id returned by the repository
    key = f"documents/{doc_id}/{filename}"
    get_storage().put(key, data)

    # 3) record the key on the row
    with get_db_session() as session:
        build_document_repository(session).set_source(doc_id, key)

    print(f"Uploaded: {key}\nDoc id:  {doc_id}\n")

    # 2) run the pipeline
    result = ingest_document(doc_id)
    print("\nRESULT:", result)
    if result.status != "ready":
        sys.exit(1)

    # 3) verify: query Pinecone filtered to this doc
    store = get_vector_store()
    hits = store.query(
        get_embeddings().embed_query("What is this document about?"),
        top_k=3,
        filter={"doc_id": {"$eq": doc_id}},
    )
    for h in hits:
        print(f"  {h['id']}  score={h['score']:.3f}  {h['metadata']['text'][:80]!r}")

    # 4) cleanup vectors + S3 (the Postgres row is left for inspection)
    store.delete_by_filter({"doc_id": {"$eq": doc_id}})
    get_storage().delete(key)
    print("\nCleaned vectors + S3. Postgres row kept for inspection (status=ready).")


if __name__ == "__main__":
    main()
