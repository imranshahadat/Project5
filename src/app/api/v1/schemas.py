"""Pydantic request/response models for the v1 API.

These are the wire format — they do NOT duplicate domain logic.
The `chat()` service returns a dict; `ChatResponse.from_result()` maps it.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

# ---------- principal ----------


class PrincipalPayload(BaseModel):
    """Caller identity. Usually extracted from headers by deps.get_principal()."""

    tenant_id: str = "public"
    subject_id: str = "anonymous"
    group_ids: list[str] = Field(default_factory=list)
    roles: list[str] = Field(default_factory=list)
    is_admin: bool = False


# ---------- chat ----------


class ChatRequest(BaseModel):
    """POST /api/v1/chat body. Principal comes from request headers."""

    question: str = Field(..., min_length=1, max_length=8000)
    thread_id: Optional[str] = Field(
        None, max_length=64, description="Resume a conversation; omitted = one-shot"
    )


class SourceRef(BaseModel):
    doc_id: str
    title: str
    chunk_index: int = 0
    score: float


class GuardrailOutcome(BaseModel):
    guard: str
    stage: str
    outcome: str  # allowed | blocked | flagged | redacted
    reason: Optional[str] = None
    snippet: Optional[str] = None
    scores: Optional[dict[str, Any]] = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceRef] = Field(default_factory=list)
    status: str  # answered | no_evidence | blocked
    thread_id: Optional[str] = None
    guardrail_outcomes: list[GuardrailOutcome] = Field(default_factory=list)
    duration_ms: float
    request_id: str

    @classmethod
    def from_result(
        cls, result: dict, thread_id: Optional[str], duration_ms: float, request_id: str
    ) -> "ChatResponse":
        return cls(
            answer=result.get("answer", ""),
            sources=result.get("sources", []),
            status=result.get("status", "answered"),
            thread_id=thread_id,
            guardrail_outcomes=result.get("guardrail_outcomes", []),
            duration_ms=round(duration_ms, 1),
            request_id=request_id,
        )


# ---------- history ----------


class HistoryItem(BaseModel):
    id: str
    role: str
    content: str
    doc_ids: Optional[list[str]] = None
    created_at: Optional[datetime] = None


class HistoryResponse(BaseModel):
    thread_id: str
    messages: list[HistoryItem]


# ---------- documents ----------


class DocumentUploadResponse(BaseModel):
    doc_id: str
    title: str
    status: str  # pending
    source: str
    metadata: dict[str, Any]
    message: str


class DocumentListItem(BaseModel):
    id: str
    title: str
    status: str  # pending | processing | ready | failed
    source: Optional[str] = None
    created_at: Optional[datetime] = None
    metadata: Optional[dict[str, Any]] = None


class DocumentListResponse(BaseModel):
    documents: list[DocumentListItem]
    total: int


class DocumentDetail(BaseModel):
    id: str
    title: str
    status: str
    source: Optional[str] = None
    content: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ---------- health ----------


class ComponentHealth(BaseModel):
    ok: bool
    detail: Optional[Any] = None


class HealthResponse(BaseModel):
    status: str  # ok | degraded | down
    components: dict[str, ComponentHealth]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ---------- errors ----------


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    request_id: str
