from abc import ABC, abstractmethod
from typing import Optional


class BaseStorage(ABC):
    """Port: any object store (S3, MinIO, R2, ...) must implement this."""

    @abstractmethod
    def put(
        self, key: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> str:
        """Store bytes under `key`. Returns a URI like 's3://bucket/key'."""
        ...

    @abstractmethod
    def get(self, key: str) -> bytes:
        """Read bytes back. Raises StorageError if missing."""
        ...

    @abstractmethod
    def delete(self, key: str) -> None: ...

    @abstractmethod
    def presigned_url(self, key: str, expires_in: Optional[int] = None) -> str:
        """Temporary GET link; provider default expiry when None."""
        ...
