"""Shared logic for all provider factories (LLM, embeddings, vector store)."""

from functools import reduce
from typing import Optional, Type, TypeVar

from app.core.config import AppSettings, get_settings
from app.core.exceptions import APIKeyMissingError, AppError, ProviderError

T = TypeVar("T")


def resolve_dotted(obj: object, dotted: str):
    """'vercel.api_key' -> obj.vercel.api_key (works with nested settings)."""
    return reduce(getattr, dotted.split("."), obj)


def build_provider(
    *,
    registry: dict[str, Type[T]],
    provider: str,
    kind: str,
    api_key_path: Optional[str],
    error: Type[ProviderError],
    settings: Optional[AppSettings] = None,
) -> T:
    """Look up `provider` in `registry`, validate its API key, instantiate it."""
    settings = settings or get_settings()

    adapter_cls = registry.get(provider)
    if adapter_cls is None:
        raise error(
            f"Unknown {kind} provider '{provider}'. "
            f"Available: {', '.join(registry)}. Check your .env."
        )

    if api_key_path:
        key = resolve_dotted(settings, api_key_path)
        get_secret = getattr(key, "get_secret_value", None)
        if key is None or (get_secret is not None and not get_secret()):
            raise APIKeyMissingError(
                f"'{api_key_path}' is missing or empty for {kind} provider '{provider}'."
            )

    try:
        return adapter_cls(settings)
    except AppError:
        raise  # already a meaningful app-level error — don't wrap it
    except Exception as e:
        raise error(f"Failed to initialise {kind} provider '{provider}': {e}") from e
