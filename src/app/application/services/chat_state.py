"""LangGraph state for the chat pipeline.

Every key is written at most once (last-write-wins reducer is fine) — no list
accumulation needed across nodes, so no ``Annotated[..., operator.add]``.
"""

from typing import Any, Optional, TypedDict


class RetrievedPassage(TypedDict):
    id: str
    score: float
    metadata: dict[str, Any]
    text: str


class SourceRef(TypedDict):
    doc_id: str
    title: str
    chunk_index: int
    score: float


class GuardrailOutcomeRecord(TypedDict):
    guard: str
    stage: str  # "input" | "output"
    outcome: str  # "allowed" | "blocked" | "flagged" | "redacted"
    reason: Optional[str]
    snippet: Optional[str]
    scores: Optional[dict[str, Any]]


class ChatState(TypedDict, total=False):
    # ---- input ----
    question: str
    principal: Any  # Principal — kept as Any so LangGraph doesn't introspect it
    thread_id: Optional[str]

    # ---- retrieve stage ----
    history: list[dict[str, Any]]
    rewritten_query: str
    query_embedding: list[float]
    access_filter: dict[str, Any]
    retrieved_passages: list[RetrievedPassage]

    # ---- guardrail ----
    input_guard_outcomes: list[GuardrailOutcomeRecord]
    output_guard_outcomes: list[GuardrailOutcomeRecord]
    blocked: bool
    block_reason: Optional[str]

    # ---- generate stage ----
    evidence_context: str
    answer: str
    sources: list[SourceRef]

    # ---- output ----
    status: str  # "answered" | "no_evidence" | "blocked"


class ChatResult(TypedDict):
    answer: str
    sources: list[SourceRef]
    status: str
    thread_id: Optional[str]
    guardrail_outcomes: list[GuardrailOutcomeRecord]
