import pytest
from app.core.config import get_settings, ProviderEnum

def test_config_loads_successfully(test_settings):
    assert test_settings is not None
    assert test_settings.embedding_provider == ProviderEnum.VERCEL
    assert test_settings.llm_provider == ProviderEnum.VERCEL

def test_database_settings(test_settings):
    assert test_settings.database.url is not None
    assert "postgresql" in test_settings.database.url.get_secret_value()

def test_guardrail_settings(test_settings):
    assert test_settings.guardrails.enabled is True
    assert test_settings.guardrails.parallel is True
    assert "pii" in test_settings.guardrails.input_guards

def test_chunking_settings_if_present(test_settings):
    if hasattr(test_settings, "chunk"):
        assert test_settings.chunk.size == 500
        assert test_settings.chunk.overlap == 50
    else:
        pytest.skip("Chunk settings not found in local AppSettings")

def test_retrieval_settings_if_present(test_settings):
    if hasattr(test_settings, "retrieval"):
        assert test_settings.retrieval.default_k == 4
        assert test_settings.retrieval.hybrid_fetch_k == 20
    else:
        pytest.skip("Retrieval settings not found in local AppSettings")
