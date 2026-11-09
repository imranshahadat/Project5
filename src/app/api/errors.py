"""Map the app's exception hierarchy to HTTP responses.

The app already has a clean exception tree rooted at AppError
(see app/core/exceptions.py). We map each branch to the right HTTP
status so callers get meaningful codes instead of a blanket 500.
"""

import logging
from typing import Union

from fastapi import Request
from fastapi.responses import JSONResponse

from app.api.v1.schemas import ErrorResponse
from app.core.exceptions import (
    APIKeyMissingError,
    AppError,
    ConfigError,
    DocumentNotFoundError,
    FileValidationError,
    ProviderError,
    StorageError,
    TextExtractionError,
    UnsupportedFileTypeError,
)

log = logging.getLogger(__name__)

# AppError subclass -> (HTTP status, error label)
_STATUS_MAP: dict[type[AppError], tuple[int, str]] = {
    ConfigError: (503, "configuration_error"),
    APIKeyMissingError: (503, "api_key_missing"),
    ProviderError: (502, "provider_error"),
    StorageError: (502, "storage_error"),
    DocumentNotFoundError: (404, "not_found"),
    FileValidationError: (400, "file_validation_error"),
    UnsupportedFileTypeError: (400, "unsupported_file_type"),
    TextExtractionError: (422, "text_extraction_error"),
}


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Handle every AppError subclass with the right status + clean body."""
    status, label = _STATUS_MAP.get(type(exc), (500, "app_error"))
    # walk MRO for subclass matches (e.g. LLMProviderError -> ProviderError)
    if status == 500:
        for cls in type(exc).__mro__:
            if cls in _STATUS_MAP:
                status, label = _STATUS_MAP[cls]
                break

    rid = _request_id(request)
    log.warning("AppError [%s] %s -> %d %s", rid, type(exc).__name__, status, exc)

    return JSONResponse(
        status_code=status,
        content=ErrorResponse(
            error=label, detail=str(exc), request_id=rid
        ).model_dump(),
    )


async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """ValueError (e.g. empty question) -> 422."""
    rid = _request_id(request)
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            error="validation_error", detail=str(exc), request_id=rid
        ).model_dump(),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all so the API never leaks a raw traceback to the caller."""
    rid = _request_id(request)
    log.exception("Unhandled exception [%s]: %s", rid, exc)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="internal_error",
            detail="An unexpected error occurred. See server logs with this request_id.",
            request_id=rid,
        ).model_dump(),
    )
