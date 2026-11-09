"""Port: append-only guardrail log (guardrail_logs table)."""

from abc import ABC, abstractmethod
from typing import Any, Optional


class BaseGuardrailLogRepository(ABC):
    @abstractmethod
    def append(
        self,
        *,
        thread_id: Optional[str],
        stage: str,  # "input" | "output"
        guard: str,
        outcome: str,  # "blocked" | "flagged" | "redacted" | "allowed"
        reason: Optional[str] = None,
        snippet: Optional[str] = None,
        scores: Optional[dict[str, Any]] = None,
    ) -> None: ...
