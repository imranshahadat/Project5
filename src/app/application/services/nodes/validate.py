"""VALIDATE node — output guardrail check on the generated answer.

Runs every configured output guard in PARALLEL. On BLOCK, swaps the answer for
a safe refusal and marks status=blocked. On REDACT, swaps in the scrubbed text.
"""

import logging
from typing import Any

from app.application.dependencies.providers import (
    build_guardrail_log_repository,
    build_output_guards,
    get_db_session,
)
from app.application.services.chat_state import ChatState, GuardrailOutcomeRecord
from app.core.config import get_settings
from app.domains.infrastructure.guardrails.runner import run_guards

log = logging.getLogger(__name__)


def validate_node(state: ChatState) -> dict[str, Any]:
    settings = get_settings()
    answer = state.get("answer", "")
    thread_id = state.get("thread_id")

    guards = build_output_guards()
    context = {
        "passages": state.get("retrieved_passages", []),
        "question": state.get("rewritten_query") or state["question"],
    }
    results = run_guards(
        guards, answer, parallel=settings.guardrails.parallel, context=context
    )

    outcomes: list[GuardrailOutcomeRecord] = []
    blocked = False
    block_reason: str | None = None
    final_answer = answer

    for name, res in results:
        outcomes.append(
            GuardrailOutcomeRecord(
                guard=name,
                stage="output",
                outcome=res.outcome,
                reason=res.reason,
                snippet=res.snippet,
                scores=res.scores,
            )
        )
        if res.outcome == "blocked":
            blocked = True
            block_reason = res.reason or "blocked by output guardrail"
        elif res.outcome == "redacted" and res.redacted_text:
            final_answer = res.redacted_text

    _persist_outcomes(thread_id, outcomes)

    update: dict[str, Any] = {"output_guard_outcomes": outcomes}
    if blocked:
        update["blocked"] = True
        update["block_reason"] = block_reason
        update["answer"] = (
            block_reason or "The response was blocked by an output guardrail."
        )
        update["status"] = "blocked"
    elif final_answer != answer:
        update["answer"] = final_answer
    return update


def _persist_outcomes(
    thread_id: str | None, outcomes: list[GuardrailOutcomeRecord]
) -> None:
    if not outcomes:
        return
    try:
        with get_db_session() as session:
            repo = build_guardrail_log_repository(session)
            for o in outcomes:
                repo.append(
                    thread_id=thread_id,
                    stage="output",
                    guard=o["guard"],
                    outcome=o["outcome"],
                    reason=o["reason"],
                    snippet=o["snippet"],
                    scores=o["scores"],
                )
    except Exception:
        log.exception("Failed to persist output guardrail logs (non-fatal)")
