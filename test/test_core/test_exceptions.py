import pytest
from app.core.exceptions import (
    AppError, ConfigError, APIKeyMissingError, ProviderError,
    LLMProviderError, EmbeddingsProviderError, VectorStoreProviderError,
    StorageError, StorageProviderError, DocumentNotFoundError,
    UnsupportedFileTypeError, TextExtractionError, FileValidationError
)

def test_exception_hierarchy():
    exceptions = [
        ConfigError, APIKeyMissingError, ProviderError, LLMProviderError,
        EmbeddingsProviderError, VectorStoreProviderError, StorageError,
        StorageProviderError, DocumentNotFoundError, UnsupportedFileTypeError,
        TextExtractionError, FileValidationError
    ]
    for exc in exceptions:
        assert issubclass(exc, AppError), f"{exc.__name__} does not inherit from AppError"

def test_api_key_missing_is_config_error():
    with pytest.raises(ConfigError):
        raise APIKeyMissingError("Missing key")
