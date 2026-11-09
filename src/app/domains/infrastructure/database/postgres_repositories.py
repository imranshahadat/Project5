"""Adapter: Postgres documents + audit repositories."""

from typing import Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from app.core.exceptions import DocumentNotFoundError
from app.domains.infrastructure.database.models import AuditEvent, Document
from app.domains.interfaces.audit import BaseAuditRepository
from app.domains.interfaces.repositories import BaseDocumentRepository


def _doc_metadata(doc: Document) -> dict[str, Any]:
    raw = doc.__dict__.get("metadata")
    if isinstance(raw, dict):
        return raw
    return {}


class PostgresDocumentRepository(BaseDocumentRepository):
    _STATUSES = {"pending", "processing", "ready", "failed"}

    def __init__(self, session: Session) -> None:
        self._session = session

    @staticmethod
    def _to_dict(doc: Document) -> dict[str, Any]:
        return {
            "id": doc.id,
            "title": doc.title,
            "content": doc.content,
            "source": doc.source,
            "status": doc.status,
            "created_at": doc.created_at,
            "updated_at": getattr(doc, "updated_at", None),
            "metadata": _doc_metadata(doc),
        }

    def add(
        self,
        title: str,
        content: str,
        source: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        doc = Document(title=title, content=content, source=source)
        if metadata is not None:
            # Safely assign metadata depending on how the column is defined in models.py
            if hasattr(doc, "meta"):
                doc.meta = metadata
            else:
                doc.__dict__["metadata"] = metadata
                try:
                    from sqlalchemy.orm.attributes import flag_modified

                    flag_modified(doc, "metadata")
                except KeyError:
                    pass  # Ignore if the SQLAlchemy mapper doesn't recognize 'metadata'

        self._session.add(doc)
        self._session.flush()
        return doc.id

    def get(self, doc_id: str) -> Optional[dict[str, Any]]:
        doc = self._session.get(Document, doc_id)
        return self._to_dict(doc) if doc else None

    def find_by_source(self, source: str) -> Optional[dict[str, Any]]:
        doc = (
            self._session.query(Document)
            .filter(Document.source == source)
            .order_by(Document.created_at.desc())
            .first()
        )
        return self._to_dict(doc) if doc else None

    def list(self, limit: int = 50) -> list[dict[str, Any]]:
        docs = (
            self._session.query(Document)
            .order_by(Document.created_at.desc())
            .limit(limit)
            .all()
        )
        return [self._to_dict(d) for d in docs]

    def update_status(self, doc_id: str, status: str) -> None:
        if status not in self._STATUSES:
            raise ValueError(
                f"Invalid status '{status}'. Allowed: {sorted(self._STATUSES)}"
            )
        doc = self._session.get(Document, doc_id)
        if doc is None:
            raise DocumentNotFoundError(f"Document '{doc_id}' not found")
        doc.status = status
        self._session.flush()

    def set_source(self, doc_id: str, source: str) -> None:
        doc = self._session.get(Document, doc_id)
        if doc is None:
            raise DocumentNotFoundError(f"Document '{doc_id}' not found")
        doc.source = source
        self._session.flush()

    def set_metadata(self, doc_id: str, metadata: dict[str, Any]) -> None:
        doc = self._session.get(Document, doc_id)
        if doc is None:
            raise DocumentNotFoundError(f"Document '{doc_id}' not found")
        doc.__dict__["metadata"] = metadata
        flag_modified(doc, "metadata")
        self._session.flush()

    def find_by_file_hash(self, file_hash: str) -> Optional[dict[str, Any]]:
        """Find a ready document with the exact same file hash in its metadata."""
        from sqlalchemy import func

        # Query PostgreSQL JSONB: meta->>'file_hash' == file_hash
        doc = (
            self._session.query(Document)
            .filter(
                Document.status == "ready",
                func.jsonb_extract_path_text(Document.meta, "file_hash") == file_hash,
            )
            .first()
        )
        return self._to_dict(doc) if doc else None


class PostgresAuditRepository(BaseAuditRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def append(
        self,
        action: str,
        entity_type: str,
        entity_id: str,
        detail: Optional[dict[str, Any]] = None,
        actor: str = "system",
    ) -> None:
        self._session.add(
            AuditEvent(
                actor=actor,
                actor_type="system",
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                detail=detail,
            )
        )
        self._session.flush()
