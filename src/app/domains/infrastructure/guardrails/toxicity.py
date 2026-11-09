"""Toxicity / banned-language guard — keyword set, configurable via env.

Ships with an EMPTY default set on purpose: your organisation's banned-word
policy is context-specific. Populate via ``TOXICITY_BANNED_WORDS=word1,word2``
in .env, or pass a set directly in tests.

This is a FILTER, not a sentiment classifier — high precision, zero cost.
For nuanced toxicity scoring add an LLM-based guard later (opt-in, parallel).
"""

from typing import Optional

from app.domains.interfaces.guardrail import BaseGuard, GuardResult


class ToxicityGuard(BaseGuard):
    name = "toxicity_filter"
    stage = "input"

    def __init__(self, banned_words: Optional[set[str]] = None) -> None:
        self._banned = {w.lower() for w in (banned_words or set()) if w}

    def check(self, text: str, context: Optional[dict] = None) -> GuardResult:
        if not self._banned:
            return GuardResult(outcome="allowed")  # not configured -> no-op
        lower = text.lower()
        hits = [w for w in self._banned if w in lower]
        if not hits:
            return GuardResult(outcome="allowed")
        return GuardResult(
            outcome="blocked",
            reason=f"Banned language detected: {len(hits)} match(es)",
            scores={"count": len(hits)},
        )
