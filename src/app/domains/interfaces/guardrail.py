"""Port: a single guardrail check (input or output)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class GuardResult:
    """Outcome of one guardrail check.

    outcome:
      - "allowed"   -> text is fine, continue
      - "redacted"  -> text was scrubbed; use `redacted_text` downstream
      - "flagged"   -> suspicious but not blocked (logged only)
      - "blocked"   -> hard stop; the pipeline must not continue / must not return this answer
    """

    outcome: str
    reason: Optional[str] = None
    snippet: Optional[str] = None  # keep SHORT — may contain PII
    scores: Optional[dict[str, Any]] = None
    redacted_text: Optional[str] = None  # only meaningful when outcome == "redacted"

    @property
    def passed(self) -> bool:
        """True if the pipeline may continue (allowed / flagged / redacted)."""
        return self.outcome != "blocked"


class BaseGuard(ABC):
    """Port: any guardrail — input or output — implements this."""

    name: str = "base"
    stage: str = "input"  # "input" | "output"

    @abstractmethod
    def check(self, text: str, context: Optional[dict[str, Any]] = None) -> GuardResult:
        """Inspect `text`. `context` carries retrieved passages etc. for output guards."""
        ...
