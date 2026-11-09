"""Adapter: Postgres chat_history table -> BaseChatHistoryRepository.

Auto-detects whether the ChatMessage model names its JSONB metadata column
``meta`` (the recommended name — SQLAlchemy reserves ``metadata``) or
``metadata`` (which some models use directly). Works with both.
"""

from typing import Any, Optional

from sqlalchemy.orm import Session

from app.domains.infrastructure.database.models import ChatMessage
from app.domains.interfaces.chat_history import BaseChatHistoryRepository

# Detect the Python attribute name for the JSONB metadata column.
# The pasted models.py used:  meta = mapped_column("metadata", JSONB)
# Your actual models.py uses:  metadata = mapped_column(JSONB)
# Support both so the repository doesn't break on either layout.
_COLUMN_ATTRS = set(ChatMessage.__mapper__.column_attrs.keys())
_META_ATTR = "meta" if "meta" in _COLUMN_ATTRS else "metadata"


class PostgresChatHistoryRepository(BaseChatHistoryRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def append(
        self,
        thread_id: str,
        role: str,
        content: str,
        doc_ids: Optional[list[str]] = None,
        meta: Optional[dict[str, Any]] = None,
    ) -> str:
        kwargs: dict[str, Any] = {
            "thread_id": thread_id,
            "role": role,
            "content": content,
            "doc_ids": doc_ids,
            _META_ATTR: meta,  # -> meta=... or metadata=... depending on model
        }
        msg = ChatMessage(**kwargs)
        self._session.add(msg)
        self._session.flush()
        return msg.id

    def get_history(self, thread_id: str, limit: int = 20) -> list[dict[str, Any]]:
        # newest `limit` rows, then reverse so caller sees oldest-first
        rows = (
            self._session.query(ChatMessage)
            .filter(ChatMessage.thread_id == thread_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
            .all()
        )
        rows = list(reversed(rows))
        return [
            {
                "id": m.id,
                "thread_id": m.thread_id,
                "role": m.role,
                "content": m.content,
                "doc_ids": m.doc_ids,
                "meta": getattr(m, _META_ATTR, None),
                "created_at": m.created_at,
            }
            for m in rows
        ]
