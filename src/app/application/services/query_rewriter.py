"""Follow-up query rewriter — at most ONE cheap LLM call per multi-turn question.

Skipped entirely when there's no chat history (first turn). Falls back to the
raw question on any error, so a slow / failed LLM call never breaks retrieval.
"""

import logging
from typing import Any

from app.application.dependencies.providers import get_llm
from app.domains.interfaces.llm import Message

log = logging.getLogger(__name__)

_SYSTEM = (
    "You are a query rewriter for retrieval. Given the user's latest question and "
    "the conversation history, produce a single self-contained search query that will "
    "retrieve the most relevant passages.\n"
    "Rules:\n"
    "- Output ONLY the rewritten query. No preamble, no quotes, no explanation.\n"
    "- If the latest question is already self-contained, return it unchanged.\n"
    "- Resolve pronouns and references using the history.\n"
    "- Keep it under 60 words."
)


def rewrite_followup_query(question: str, history: list[dict[str, Any]]) -> str:
    """Turn a follow-up question into a self-contained search query (1 LLM call)."""
    if not history:
        return question

    try:
        # last 6 turns is enough context for coreference and cheap on tokens
        history_text = "\n".join(
            f"{m['role']}: {m['content']}" for m in history[-6:]
        )
        messages = [
            Message(role="system", content=_SYSTEM),
            Message(
                role="user",
                content=(
                    f"Conversation so far:\n{history_text}\n\n"
                    f"Latest question: {question}\n\n"
                    f"Rewritten search query:"
                ),
            ),
        ]
        rewritten = get_llm().generate(messages).strip().strip('"').strip("'")

        # guardrail on the rewriter itself — never let a runaway response through
        if not rewritten or len(rewritten) > 500:
            log.warning("Query rewrite returned unusable output; using raw question")
            return question
        return rewritten
    except Exception:
        log.exception("Query rewrite failed — using raw question")
        return question
