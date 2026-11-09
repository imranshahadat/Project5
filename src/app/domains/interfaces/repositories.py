# domains/interfaces/repositories.py  — PORT, vendor-neutral
from abc import ABC, abstractmethod
from typing import Optional


class BaseDocumentRepository(ABC):
    @abstractmethod
    def add(self, title: str, content: str, source: Optional[str] = None) -> str: ...

    @abstractmethod
    def get(self, doc_id: str) -> Optional[dict]:
        """-> {'id','title','content','source','status','created_at'} or None."""

    @abstractmethod
    def list(self, limit: int = 50) -> list[dict]: ...

    @abstractmethod
    def update_status(self, doc_id: str, status: str) -> None:
        """pending | processing | ready | failed (also guarded by DB CHECK)."""

    @abstractmethod
    def set_source(self, doc_id: str, source: str) -> None:
        """Attach the storage key (e.g. S3 URI) after the file is uploaded."""

    @abstractmethod
    def find_by_source(self, source: str) -> Optional[dict]:
        """Latest row whose `source` == storage key, or None."""
