"""SQLAlchemy models — source of truth for the schema.

Mirrors db/reference_schema.sql. scripts/init_db.py builds from these models.
"""

from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _uuid() -> str:
    return str(uuid4())


class Base(DeclarativeBase):
    pass


# --------------------------------------------------------------- documents
class Document(Base):
    """Ingested documents + ingestion metadata."""

    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String(512))
    content: Mapped[str] = mapped_column(Text)
    source: Mapped[Optional[str]] = mapped_column(String(512))  # URL / file path
    status: Mapped[str] = mapped_column(
        String(20), default="pending", server_default="pending"
    )  # pending | processing | ready | failed
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','processing','ready','failed')",
            name="ck_documents_status",
        ),
        Index("ix_documents_status_created", "status", "created_at"),
    )


# ------------------------------------------------------------ chat history
class ChatMessage(Base):
    """One turn of a conversation — the agent's persistent memory."""

    __tablename__ = "chat_history"  # one conversation == one thread_id

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    thread_id: Mapped[str] = mapped_column(String(64))
    role: Mapped[str] = mapped_column(String(16))  # system | user | assistant | tool
    content: Mapped[str] = mapped_column(Text)
    doc_ids: Mapped[Optional[list[Any]]] = mapped_column(JSONB)  # RAG sources used
    # NB: attribute must NOT be called `metadata` — SQLAlchemy reserves it
    meta: Mapped[Optional[dict[str, Any]]] = mapped_column("metadata", JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "role IN ('system','user','assistant','tool')",
            name="ck_chat_history_role",
        ),
        Index("ix_chat_history_thread_created", "thread_id", "created_at"),
    )


# --------------------------------------------------- approvals (HITL)
class Approval(Base):
    """Human-in-the-loop request: agent asks, human approves/rejects."""

    __tablename__ = "approvals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    thread_id: Mapped[str] = mapped_column(String(64))
    request_type: Mapped[str] = mapped_column(
        String(64)
    )  # e.g. "send_email", "run_tool"
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)  # what the agent wants to do
    status: Mapped[str] = mapped_column(
        String(16), default="pending", server_default="pending"
    )  # pending | approved | rejected | expired
    requested_by: Mapped[Optional[str]] = mapped_column(String(128))
    decided_by: Mapped[Optional[str]] = mapped_column(String(128))
    decision_note: Mapped[Optional[str]] = mapped_column(Text)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','approved','rejected','expired')",
            name="ck_approvals_status",
        ),
        Index("ix_approvals_thread_id", "thread_id"),
        Index("ix_approvals_status_requested", "status", "requested_at"),
    )


# ----------------------------------------------------------------- feedback
class Feedback(Base):
    """User feedback tied to a thread, optionally to one message."""

    __tablename__ = "feedback"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    thread_id: Mapped[str] = mapped_column(String(64))
    message_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("chat_history.id", ondelete="SET NULL")
    )
    rating: Mapped[Optional[int]] = mapped_column(SmallInteger)  # 1..5
    is_helpful: Mapped[Optional[bool]] = mapped_column(Boolean)  # thumbs up/down
    category: Mapped[Optional[str]] = mapped_column(String(64))  # e.g. "accuracy"
    comment: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "rating IS NULL OR rating BETWEEN 1 AND 5", name="ck_feedback_rating"
        ),
        Index("ix_feedback_thread_id", "thread_id"),
    )


# ------------------------------------------------------------- audit events
class AuditEvent(Base):
    """Append-only trail: who did what, to what, when."""

    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    actor: Mapped[str] = mapped_column(
        String(128), default="system", server_default="system"
    )
    actor_type: Mapped[str] = mapped_column(
        String(16), default="system", server_default="system"
    )  # user | agent | system
    action: Mapped[str] = mapped_column(String(128))  # e.g. "approval.granted"
    entity_type: Mapped[Optional[str]] = mapped_column(String(64))  # "document", ...
    entity_id: Mapped[Optional[str]] = mapped_column(String(36))
    detail: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))  # IPv6-safe
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "actor_type IN ('user','agent','system')", name="ck_audit_actor_type"
        ),
        Index("ix_audit_action_created", "action", "created_at"),
        Index("ix_audit_entity", "entity_type", "entity_id"),
    )


# ----------------------------------------------------------- guardrail logs
class GuardrailLog(Base):
    """Blocked/flagged/redacted events from input & output guardrails."""

    __tablename__ = "guardrail_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    thread_id: Mapped[Optional[str]] = mapped_column(String(64))
    stage: Mapped[str] = mapped_column(String(16))  # input | output
    guard: Mapped[str] = mapped_column("guardrail", String(64))  # e.g. "pii_filter"
    outcome: Mapped[str] = mapped_column(
        String(16)
    )  # blocked | flagged | redacted | allowed
    reason: Mapped[Optional[str]] = mapped_column(Text)
    snippet: Mapped[Optional[str]] = mapped_column(Text)  # keep SHORT — may contain PII
    scores: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint("stage IN ('input','output')", name="ck_guardrail_stage"),
        CheckConstraint(
            "outcome IN ('blocked','flagged','redacted','allowed')",
            name="ck_guardrail_outcome",
        ),
        Index("ix_guardrail_thread_id", "thread_id"),
        Index("ix_guardrail_outcome_created", "outcome", "created_at"),
    )
