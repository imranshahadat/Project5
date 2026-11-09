"""GET /health — cheap connectivity probe for load balancers / smoke tests.

Checks DB, vector store, and LLM provider in parallel (asyncio.gather).
Each check is offloaded to a thread because the underlying adapters are sync.
"""

import asyncio
import logging
from datetime import datetime

from fastapi import APIRouter

from app.api.v1.schemas import ComponentHealth, HealthResponse

log = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


async def _check_db() -> ComponentHealth:
    def _probe():
        from app.domains.infrastructure.database.engine import check_database

        return check_database()

    try:
        result = await asyncio.to_thread(_probe)
        return ComponentHealth(ok=True, detail={"server": result.get("server")})
    except Exception as e:
        log.warning("health: DB check failed: %s", e)
        return ComponentHealth(ok=False, detail=str(e)[:200])


async def _check_vector_store() -> ComponentHealth:
    def _probe():
        from app.application.dependencies.providers import get_vector_store

        return get_vector_store().stats()

    try:
        stats = await asyncio.to_thread(_probe)
        return ComponentHealth(ok=True, detail=stats)
    except Exception as e:
        log.warning("health: vector store check failed: %s", e)
        return ComponentHealth(ok=False, detail=str(e)[:200])


async def _check_llm() -> ComponentHealth:
    def _probe():
        from app.application.dependencies.providers import get_llm

        get_llm()  # just verify it builds — no actual call
        return True

    try:
        await asyncio.to_thread(_probe)
        return ComponentHealth(ok=True)
    except Exception as e:
        log.warning("health: LLM check failed: %s", e)
        return ComponentHealth(ok=False, detail=str(e)[:200])


@router.get("", response_model=HealthResponse, summary="Service health")
async def health() -> HealthResponse:
    """Parallel probe of DB + vector store + LLM provider."""
    results = await asyncio.gather(_check_db(), _check_vector_store(), _check_llm())
    components = {"database": results[0], "vector_store": results[1], "llm": results[2]}
    all_ok = all(c.ok for c in components.values())
    return HealthResponse(
        status="ok" if all_ok else "degraded",
        components=components,
        timestamp=datetime.utcnow(),
    )
