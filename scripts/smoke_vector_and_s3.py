"""End-to-end smoke test: S3 roundtrip + Pinecone roundtrip.

Run from Project4/:  python scripts/smoke_vector_and_s3.py
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from app.application.dependencies.providers import (  # noqa: E402
    get_embeddings,
    get_storage,
    get_vector_store,
)

TEXT = "Pinecone smoke test chunk — delete me."


def main() -> None:
    # ---- S3 ----
    storage = get_storage()
    key = f"smoke/test-{int(time.time())}.txt"
    uri = storage.put(key, b"hello from Project4", content_type="text/plain")
    assert storage.get(key) == b"hello from Project4"
    print("S3 OK:", uri)
    print("Presigned:", storage.presigned_url(key)[:80], "...")
    storage.delete(key)
    print("S3 cleaned up\n")

    # ---- Pinecone ----
    vectors = get_embeddings()
    store = get_vector_store()
    print("Vector store stats:", store.stats())

    doc_id = "smoke-demo-doc"
    vec = vectors.embed_query(TEXT)
    store.upsert(
        ids=["smoke-0001"],
        vectors=[vec],
        metadatas=[{"doc_id": doc_id, "chunk_index": 0, "text": TEXT}],
    )
    hits = store.query(vec, top_k=3)
    print("Query hits:", [(h["id"], round(h["score"], 3)) for h in hits])

    store.delete_by_filter({"doc_id": {"$eq": doc_id}})
    print("Pinecone cleaned up")


if __name__ == "__main__":
    main()
