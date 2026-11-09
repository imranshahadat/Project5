from abc import ABC, abstractmethod
from typing import Any, Optional


class BaseAuditRepository(ABC):
    """Port: append-only audit trail (audit_events table)."""

    @abstractmethod
    def append(
        self,
        action: str,
        entity_type: str,
        entity_id: str,
        detail: Optional[dict[str, Any]] = None,
        actor: str = "system",
    ) -> None: ...
