"""FastAPI application factory.

The API layer is a thin transport adapter:
  - calls `chat()` from app.application.services — no business logic here
  - maps AppError -> HTTP via app/api/errors.py
  - offloads sync pipeline calls to a thread pool (asyncio.to_thread)
  - wires request-ID + timing middleware
  - lifespan: warms the lru_cache singletons at startup so the first
    request doesn't pay the provider-init latency

Run:
    uvicorn app.api.main:app --reload
    # or
    python scripts/run_api.py
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from app.api.errors import (
    app_error_handler,
    unhandled_exception_handler,
    value_error_handler,
)
from app.api.middleware import RequestIDMiddleware
from app.api.v1.router import v1_router
from app.core.exceptions import AppError

log = logging.getLogger(__name__)

# Terminal chat UI — served at GET /
_STATIC_DIR = Path(__file__).resolve().parent / "static"
_INDEX_HTML = _STATIC_DIR / "index.html"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Warm up caches + configure logging at startup; noop on shutdown."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-5s %(name)s: %(message)s",
    )
    # Pre-build the graph + providers so the first request is fast.
    # These are lru_cached — if they fail, the error surfaces here
    # (fail-fast at boot) rather than on the first user request.
    try:
        from app.application.services.chat import build_chat_graph

        build_chat_graph.cache_clear()
        build_chat_graph()  # compile the LangGraph
        log.info("startup: chat graph compiled")
    except Exception as e:
        # Non-fatal: the graph will build lazily on first request.
        # Providers may not be configured yet (e.g. during local dev).
        log.warning("startup: could not pre-build chat graph: %s", e)

    yield
    log.info("shutdown: cleaning up")


def create_app() -> FastAPI:
    app = FastAPI(
        title="RAG Chat API",
        version="1.0.0",
        description="Retrieval-augmented chat with parallel guardrails.",
        lifespan=lifespan,
    )

    # ---- middleware (order: last added = outermost) ----
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # tighten in production
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    # ---- exception handlers ----
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(ValueError, value_error_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    # ---- routes ----
    app.include_router(v1_router)

    @app.get("/", include_in_schema=False)
    async def index():
        """Serve the terminal chat UI."""
        if _INDEX_HTML.is_file():
            return HTMLResponse(_INDEX_HTML.read_text(encoding="utf-8"))
        return HTMLResponse(
            "<h1>RAG Chat API</h1><p>UI not found at {}</p>".format(_INDEX_HTML),
            status_code=404,
        )

    return app


app = create_app()
