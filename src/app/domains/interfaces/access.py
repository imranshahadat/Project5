"""Port: caller identity + access-filter builder for vector-store queries."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Principal:
    """Caller identity. Immutable — safe to cache / pass through graph state.

    Mirrors the 'TENANT / GROUP / SUBJECT' access filter in the flow diagram.
    """

    tenant_id: str
    subject_id: str  # user / service id
    group_ids: tuple[str, ...] = field(default=())
    roles: tuple[str, ...] = field(default=())
    is_admin: bool = False

    @classmethod
    def anonymous(cls) -> "Principal":
        """Unauthenticated / local-dev — tenant 'public', no groups."""
        return cls(tenant_id="public", subject_id="anonymous")


class BaseAccessFilterBuilder(ABC):
    """Port: turn a Principal into a vendor-neutral filter dict.

    The dict shape matches the vector-store port's `query(filter=...)` argument,
    so Pinecone / pgvector / Weaviate adapters each translate it as needed.
    """

    @abstractmethod
    def build(self, principal: Principal) -> dict[str, Any]: ...
