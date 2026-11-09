"""NO_EVIDENCE node — returned when no passage cleared the relevance threshold.

Uses a configurable static message (no LLM call -> zero cost / zero latency).
The exchange is still persisted so you can analyse coverage gaps later.
"""

import logging
from typing import Any

from app.application.dependencies.providers import (
    build_chat_history_repository,
    get_db_session,
)
from app.application.services.chat_state import ChatState
from app.core.config import get_settings

log = logging.getLogger(__name__)


def no_evidence_node(state: ChatState) -> dict[str, Any]:
    settings = get_settings()
    message = settings.chat.no_evidence_message

    thread_id = state.get("thread_id")
    if thread_id:
        try:
            with get_db_session() as session:
                repo = build_chat_history_repository(session)
                repo.append(thread_id, "user", state["question"])
                repo.append(thread_id, "assistant", message)
        except Exception:
            log.exception("Failed to persist no-evidence exchange (non-fatal)")

    log.info("no_evidence: thread=%s question=%r", thread_id, state["question"][:80])
    return {
        "answer": message,
        "sources": [],
        "status": "no_evidence",
    }
