from typing import Optional

from app.core.config import AppSettings, get_settings
from app.core.exceptions import VectorStoreProviderError
from app.domains.infrastructure._builder import build_provider
from app.domains.infrastructure.vector_store.pinecone import PineconeVectorStore
from app.domains.interfaces.vector_store import BaseVectorStore

VECTOR_STORE_REGISTRY: dict[str, type[BaseVectorStore]] = {
    "pinecone": PineconeVectorStore,
    # "aws_aurora_pgvector": ...,  # <- future adapter goes here
}

API_KEY_REQUIREMENTS: dict[str, str] = {
    "pinecone": "pinecone.api_key",
}


def build_vector_store(settings: Optional[AppSettings] = None) -> BaseVectorStore:
    s = settings or get_settings()
    provider = s.vector_store_provider.value.lower()
    return build_provider(
        registry=VECTOR_STORE_REGISTRY,
        provider=provider,
        kind="vector store",
        api_key_path=API_KEY_REQUIREMENTS.get(provider),
        error=VectorStoreProviderError,
        settings=s,
    )
