import pytest
from app.application.dependencies.providers import get_llm, get_embeddings, get_vector_store, get_storage, reset_all_caches
from app.core.config import get_settings
from app.core.exceptions import ConfigError, APIKeyMissingError

def test_pipeline_wiring_llm():
    reset_all_caches()
    get_settings.cache_clear()
    try:
        assert get_llm() is not None
    except (ConfigError, APIKeyMissingError) as e:
        pytest.skip(f"LLM provider skipped: {e}")

def test_pipeline_wiring_embeddings():
    reset_all_caches()
    get_settings.cache_clear()
    try:
        assert get_embeddings() is not None
    except (ConfigError, APIKeyMissingError) as e:
        pytest.skip(f"Embeddings provider skipped: {e}")

def test_pipeline_wiring_vector_store(mock_pinecone):
    reset_all_caches()
    get_settings.cache_clear()
    try:
        vector_store = get_vector_store()
        assert vector_store is not None
        mock_pinecone.assert_called_once()
    except (ConfigError, APIKeyMissingError) as e:
        pytest.skip(f"Vector store safely skipped: {e}")

def test_pipeline_wiring_storage():
    reset_all_caches()
    get_settings.cache_clear()
    try:
        assert get_storage() is not None
    except (ConfigError, APIKeyMissingError) as e:
        pytest.skip(f"Storage provider skipped: {e}")
