"""FastAPI dependency providers.

These bridge FastAPI's DI into the app's existing composition root
(`app.application.dependencies.providers`). No business logic here.
"""

from typing import Annotated, Optional

from fastapi import Header

from app.domains.interfaces.access import Principal


def get_principal(
    x_tenant_id: Annotated[Optional[str], Header()] = None,
    x_subject_id: Annotated[Optional[str], Header()] = None,
    x_groups: Annotated[Optional[str], Header()] = None,
    x_roles: Annotated[Optional[str], Header()] = None,
    x_is_admin: Annotated[Optional[str], Header()] = None,
) -> Principal:
    """Build a Principal from request headers.

    In production these headers are set by your auth gateway / JWT middleware.
    For local dev they default to anonymous (tenant='public', no groups).

    Header → Principal mapping:
      X-Tenant-Id   -> tenant_id
      X-Subject-Id  -> subject_id
      X-Groups      -> group_ids (CSV)
      X-Roles       -> roles (CSV)
      X-Is-Admin    -> is_admin (truthy: "1","true","yes")
    """

    def _csv(value: Optional[str]) -> tuple[str, ...]:
        if not value:
            return ()
        return tuple(p.strip() for p in value.split(",") if p.strip())

    return Principal(
        tenant_id=x_tenant_id or "public",
        subject_id=x_subject_id or "anonymous",
        group_ids=_csv(x_groups),
        roles=_csv(x_roles),
        is_admin=(x_is_admin or "").strip().lower() in ("1", "true", "yes"),
    )


PrincipalDep = Annotated[Principal, "principal"]
