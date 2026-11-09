"""Adapter: Postgres guardrail_logs table -> BaseGuardrailLogRepository."""

from typing import Any, Optional

from sqlalchemy.orm import Session

from app.domains.infrastructure.database.models import GuardrailLog
from app.domains.interfaces.guardrail_log import BaseGuardrailLogRepository


class PostgresGuardrailLogRepository(BaseGuardrailLogRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def append(
        self,
        *,
        thread_id: Optional[str],
        stage: str,
        guard: str,
        outcome: str,
        reason: Optional[str] = None,
        snippet: Optional[str] = None,
        scores: Optional[dict[str, Any]] = None,
    ) -> None:
        self._session.add(
            GuardrailLog(
                thread_id=thread_id,
                stage=stage,
                guard=guard,
                outcome=outcome,
                reason=reason,
                snippet=snippet,
                scores=scores,
            )
        )
        self._session.flush()
