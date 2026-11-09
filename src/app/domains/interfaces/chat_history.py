"""Port: conversation memory (chat_history table)."""

from abc import ABC, abstractmethod
from typing import Any, Optional


class BaseChatHistoryRepository(ABC):
    @abstractmethod
    def append(
        self,
        thread_id: str,
        role: str,  # system | user | assistant | tool
        content: str,
        doc_ids: Optional[list[str]] = None,
        meta: Optional[dict[str, Any]] = None,
    ) -> str:
        """Persist one message. Returns its id."""
        ...

    @abstractmethod
    def get_history(self, thread_id: str, limit: int = 20) -> list[dict[str, Any]]:
        """Return the most recent `limit` messages, oldest-first.

        Each item: {'id','thread_id','role','content','doc_ids','meta','created_at'}.
        """
        ...
