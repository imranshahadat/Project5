"""POST /chat  +  GET /chat/history/{thread_id}

The chat endpoint runs the sync `chat()` call in a thread pool via
`asyncio.to_thread()` so the event loop stays free during the LLM call
(500-2000ms). Multiple concurrent chat requests are served in parallel.
"""

import asyncio
import logging
import time

from fastapi import APIRouter, Depends, Request

from app.api.deps import get_principal
from app.api.v1.schemas import (
    ChatRequest,
    ChatResponse,
    HistoryResponse,
    PrincipalPayload,
)
from app.application.dependencies.providers import (
    build_chat_history_repository,
    get_db_session,
)
from app.application.services.chat import chat
from app.domains.interfaces.access import Principal

log = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse, summary="Ask a question")
async def chat_endpoint(
    request: Request,
    body: ChatRequest,
    principal: Principal = Depends(get_principal),
) -> ChatResponse:
    """Run the full RAG pipeline: guard -> retrieve -> generate -> validate.

    The sync `chat()` runs in a worker thread so this endpoint remains
    non-blocking. Returns the answer, sources, status, and guardrail outcomes.
    """
    rid = getattr(request.state, "request_id", "unknown")
    start = time.perf_counter()

    # Offload the sync pipeline to a thread — the event loop handles
    # other HTTP requests while the LLM call is in flight.
    result = await asyncio.to_thread(chat, principal, body.question, body.thread_id)

    duration_ms = (time.perf_counter() - start) * 1000
    log.info(
        "chat [%s] status=%s sources=%d duration=%.0fms",
        rid,
        result.get("status"),
        len(result.get("sources", [])),
        duration_ms,
    )
    return ChatResponse.from_result(result, body.thread_id, duration_ms, rid)


@router.get(
    "/history/{thread_id}",
    response_model=HistoryResponse,
    summary="Load conversation history",
)
async def get_history(thread_id: str) -> HistoryResponse:
    """Return the most recent messages for a thread (oldest-first)."""
    with get_db_session() as session:
        repo = build_chat_history_repository(session)
        messages = repo.get_history(thread_id, limit=50)
    return HistoryResponse(thread_id=thread_id, messages=messages)
