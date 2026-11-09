from abc import ABC, abstractmethod
from typing import Any, Optional


class BaseVectorStore(ABC):
    """Port: any vector database must implement this."""

    @abstractmethod
    def upsert(
        self,
        ids: list[str],
        vectors: list[list[float]],
        metadatas: list[dict[str, Any]],
    ) -> int:
        """Insert/update vectors with metadata. Returns number written."""
        ...

    @abstractmethod
    def query(
        self,
        vector: list[float],
        top_k: int = 4,
        filter: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        """Nearest-neighbour search -> [{'id', 'score', 'metadata'}, ...]."""
        ...

    @abstractmethod
    def delete_by_filter(self, filter: dict[str, Any]) -> None:
        """Delete all vectors matching `filter` (e.g. one document's chunks)."""
        ...

    @abstractmethod
    def stats(self) -> dict[str, Any]:
        """Cheap health/debug probe (total vectors, dimension, ...)."""
        ...
