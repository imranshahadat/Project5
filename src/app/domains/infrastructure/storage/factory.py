from typing import Optional

from app.core.config import AppSettings, get_settings
from app.core.exceptions import StorageProviderError
from app.domains.infrastructure._builder import build_provider
from app.domains.infrastructure.storage.s3 import S3Storage
from app.domains.interfaces.storage import BaseStorage

STORAGE_REGISTRY: dict[str, type[BaseStorage]] = {
    "aws": S3Storage,
}

API_KEY_REQUIREMENTS: dict[str, str] = {
    # Remove this entry to fall back to boto3's default credential chain (IAM role).
    "aws": "aws.secret_access_key",
}


def build_storage(settings: Optional[AppSettings] = None) -> BaseStorage:
    s = settings or get_settings()
    provider = s.storage_provider.value.lower()
    return build_provider(
        registry=STORAGE_REGISTRY,
        provider=provider,
        kind="storage",
        api_key_path=API_KEY_REQUIREMENTS.get(provider),
        error=StorageProviderError,
        settings=s,
    )
