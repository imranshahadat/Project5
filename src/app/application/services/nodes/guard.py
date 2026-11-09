"""GUARD node — input guardrail check.

Runs every configured input guard in PARALLEL (ThreadPoolExecutor), persists
outcomes to guardrail_logs, and:
  - on BLOCK  -> sets blocked=True + status=blocked, the graph routes to END
  - on REDACT -> swaps the question for the redacted version downstream
  - on ALLOW / FLAG -> continue unchanged
"""

import logging
from typing import Any

from app.application.dependencies.providers import (
    build_guardrail_log_repository,
    build_input_guards,
    get_db_session,
)
from app.application.services.chat_state import ChatState, GuardrailOutcomeRecord
from app.core.config import get_settings
from app.domains.infrastructure.guardrails.runner import run_guards

log = logging.getLogger(__name__)


def guard_node(state: ChatState) -> dict[str, Any]:
    question = state["question"]
    thread_id = state.get("thread_id")
    settings = get_settings()

    guards = build_input_guards()
    results = run_guards(
        guards, question, parallel=settings.guardrails.parallel
    )

    outcomes: list[GuardrailOutcomeRecord] = []
    blocked = False
    block_reason: str | None = None
    redacted_question = question

    for name, res in results:
        outcomes.append(
            GuardrailOutcomeRecord(
                guard=name,
                stage="input",
                outcome=res.outcome,
                reason=res.reason,
                snippet=res.snippet,
                scores=res.scores,
            )
        )
        if res.outcome == "blocked":
            blocked = True
            block_reason = res.reason or "blocked by input guardrail"
        elif res.outcome == "redacted" and res.redacted_text:
            redacted_question = res.redacted_text

    _persist_outcomes(thread_id, outcomes)

    update: dict[str, Any] = {
        "input_guard_outcomes": outcomes,
        "blocked": blocked,
    }
    if blocked:
        update["block_reason"] = block_reason
        update["status"] = "blocked"
        update["answer"] = (
            block_reason or "Your question was blocked by an input guardrail."
        )
    elif redacted_question != question:
        update["rewritten_query"] = redacted_question

    return update


def _persist_outcomes(thread_id: str | None, outcomes: list[GuardrailOutcomeRecord]) -> None:
    if not outcomes:
        return
    try:
        with get_db_session() as session:
            repo = build_guardrail_log_repository(session)
            for o in outcomes:
                repo.append(
                    thread_id=thread_id,
                    stage="input",
                    guard=o["guard"],
                    outcome=o["outcome"],
                    reason=o["reason"],
                    snippet=o["snippet"],
                    scores=o["scores"],
                )
    except Exception:
        log.exception("Failed to persist input guardrail logs (non-fatal)")
