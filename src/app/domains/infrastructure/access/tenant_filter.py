"""Adapter: build a Pinecone metadata filter from a Principal.

Filter logic (when enabled):
    visible IF  tenant_id == principal.tenant_id
              OR tenant_id == "public"
              OR document shared with one of principal.group_ids
              OR document shared directly with principal.subject_id

NOTE — ingestion must tag chunks with these metadata keys for the filter to
match anything. Until then, keep ``ACCESS_CONTROL_ENABLED=false`` (the default)
so the builder returns ``{}`` (no filter) and retrieval sees everything.
"""

from typing import Any

from app.core.config import AppSettings
from app.domains.interfaces.access import BaseAccessFilterBuilder, Principal


class TenantAccessFilterBuilder(BaseAccessFilterBuilder):
    def __init__(self, settings: AppSettings) -> None:
        self._enabled = settings.access_control.enabled

    def build(self, principal: Principal) -> dict[str, Any]:
        if not self._enabled:
            return {}
        if principal.is_admin:
            return {}  # admin sees everything

        clauses: list[dict[str, Any]] = [
            {"tenant_id": {"$eq": principal.tenant_id}},
            {"tenant_id": {"$eq": "public"}},
        ]
        if principal.group_ids:
            clauses.append({"shared_groups": {"$in": list(principal.group_ids)}})
        clauses.append({"shared_subjects": {"$in": [principal.subject_id]}})

        return {"$or": clauses}
