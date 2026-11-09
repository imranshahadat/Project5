"""PII guard — regex-based, zero dependencies, zero cost.

Detects: email, phone (US), SSN, credit-card-shaped numbers.
Input variant: redact by default (don't block the user, just scrub).
Output variant: block by default (never let the model leak PII back).

To upgrade to higher-recall PII detection without changing the graph,
swap the regexes here for Microsoft Presidio (``presidio-analyzer``) —
the ``BaseGuard`` contract stays identical.
"""

import re
from typing import Any, Optional

from app.domains.interfaces.guardrail import BaseGuard, GuardResult

_PII_PATTERNS: dict[str, re.Pattern] = {
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "phone": re.compile(
        r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
    ),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    # Matches 13-19 digit runs (optionally spaced/dashed) — quick & conservative.
    "card": re.compile(r"\b(?:\d[ -]*?){13,19}\b"),
}

_REDACT = "[REDACTED]"


def _scan(text: str) -> tuple[dict[str, int], str]:
    """Return (counts_by_kind, redacted_text)."""
    counts: dict[str, int] = {}
    redacted = text
    for kind, pat in _PII_PATTERNS.items():
        matches = pat.findall(text)
        if matches:
            counts[kind] = len(matches)
            redacted = pat.sub(_REDACT, redacted)
    return counts, redacted


class PIIInputGuard(BaseGuard):
    name = "pii_filter"
    stage = "input"

    def __init__(self, *, block: bool = False) -> None:
        """``block=True`` -> reject the question; ``block=False`` -> redact & continue."""
        self._block = block

    def check(self, text: str, context: Optional[dict] = None) -> GuardResult:
        counts, redacted = _scan(text)
        if not counts:
            return GuardResult(outcome="allowed")
        if self._block:
            return GuardResult(
                outcome="blocked",
                reason=f"PII detected in input: {counts}",
                scores={"counts": counts},
            )
        return GuardResult(
            outcome="redacted",
            reason=f"PII redacted from input: {counts}",
            scores={"counts": counts},
            redacted_text=redacted,
        )


class PIIOutputGuard(BaseGuard):
    name = "pii_filter"
    stage = "output"

    def __init__(self, *, block: bool = True) -> None:
        """Output default is to BLOCK — never leak PII the model echoed from context."""
        self._block = block

    def check(self, text: str, context: Optional[dict] = None) -> GuardResult:
        counts, redacted = _scan(text)
        if not counts:
            return GuardResult(outcome="allowed")
        if self._block:
            return GuardResult(
                outcome="blocked",
                reason=f"PII leaked in model output: {counts}",
                scores={"counts": counts},
                snippet=redacted[:200],
            )
        return GuardResult(
            outcome="redacted",
            reason=f"PII redacted from output: {counts}",
            scores={"counts": counts},
            redacted_text=redacted,
        )
