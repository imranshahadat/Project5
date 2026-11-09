"""Lightweight middleware: request ID + response timing header.

No heavy logic — just observability hooks so every log line and error
response can be correlated to a single request.
"""

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach a request_id to request.state + set it as a response header.

    If the caller provides X-Request-ID, we honour it (useful for distributed
    tracing). Otherwise we generate one.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        request.state.request_id = rid

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        response.headers["X-Request-ID"] = rid
        response.headers["X-Response-Time-ms"] = f"{duration_ms:.1f}"
        return response
