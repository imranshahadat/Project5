"""Adapter: Pinecone serverless index -> BaseVectorStore port.

Uses PINECONE_INDEX_NAME to resolve the serverless index automatically.
PINECONE_ENVIRONMENT is legacy/unused for serverless.
"""

from typing import Any, Optional

from pinecone import Pinecone

from app.core.config import AppSettings
from app.core.exceptions import APIKeyMissingError
from app.domains.interfaces.vector_store import BaseVectorStore

UPSERT_BATCH = 100


class PineconeVectorStore(BaseVectorStore):
    def __init__(self, settings: AppSettings) -> None:
        cfg = settings.pinecone
        api_key = cfg.api_key

        if not api_key or not api_key.get_secret_value():
            raise APIKeyMissingError("PINECONE_API_KEY is empty. Add it to your .env.")

        if not cfg.index_name:
            raise APIKeyMissingError(
                "PINECONE_INDEX_NAME is empty. Add your Pinecone index name."
            )

        # Initialize Pinecone client
        pc = Pinecone(api_key=api_key.get_secret_value())

        # IMPORTANT: Use name=, NOT host=
        self._index = pc.Index(name=cfg.index_name)

        self._namespace = cfg.namespace or None

    def upsert(
        self,
        ids: list[str],
        vectors: list[list[float]],
        metadatas: list[dict[str, Any]],
    ) -> int:

        if not (len(ids) == len(vectors) == len(metadatas)):
            raise ValueError("ids, vectors and metadatas must have the same length")

        written = 0

        for i in range(0, len(ids), UPSERT_BATCH):
            batch = [
                {
                    "id": _id,
                    "values": vec,
                    "metadata": meta,
                }
                for _id, vec, meta in zip(
                    ids[i : i + UPSERT_BATCH],
                    vectors[i : i + UPSERT_BATCH],
                    metadatas[i : i + UPSERT_BATCH],
                )
            ]

            resp = self._index.upsert(
                vectors=batch,
                namespace=self._namespace,
            )

            written += resp.get("upserted_count", len(batch))

        return written

    def query(
        self,
        vector: list[float],
        top_k: int = 4,
        filter: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:

        resp = self._index.query(
            vector=vector,
            top_k=top_k,
            namespace=self._namespace,
            filter=filter,
            include_metadata=True,
        )

        return [
            {
                "id": m["id"],
                "score": float(m["score"]),
                "metadata": m.get("metadata", {}),
            }
            for m in resp.get("matches", [])
        ]

    def delete_by_filter(self, filter: dict[str, Any]) -> None:
        self._index.delete(
            filter=filter,
            namespace=self._namespace,
        )

    def stats(self) -> dict[str, Any]:
        return dict(self._index.describe_index_stats())
