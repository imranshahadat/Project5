from typing import Optional

from app.core.config import AppSettings, get_settings
from app.core.exceptions import EmbeddingsProviderError
from app.domains.infrastructure._builder import build_provider
from app.domains.interfaces.embeddings import BaseEmbeddings
from app.domains.infrastructure.embeddings.vercel import VercelEmbeddings

EMBEDDINGS_REGISTRY: dict[str, type[BaseEmbeddings]] = {
    "vercel": VercelEmbeddings,
}

API_KEY_REQUIREMENTS: dict[str, str] = {
    "vercel": "vercel.api_key",
}


def build_embeddings(settings: Optional[AppSettings] = None) -> BaseEmbeddings:
    s = settings or get_settings()
    provider = s.embedding_provider.value.lower()
    return build_provider(
        registry=EMBEDDINGS_REGISTRY,
        provider=provider,
        kind="embeddings",
        api_key_path=API_KEY_REQUIREMENTS.get(provider),
        error=EmbeddingsProviderError,
        settings=s,
    )
