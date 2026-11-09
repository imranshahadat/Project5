import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

BASE_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = BASE_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test_db")
os.environ.setdefault("VERCEL_API_KEY", "test_vercel_api_key_for_startup_check")

from app.core.config import get_settings

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()

@pytest.fixture(scope="session")
def test_settings():
    return get_settings()

@pytest.fixture
def mock_pinecone():
    with patch("app.domains.infrastructure.vector_store.pinecone.Pinecone") as mock_pc_class:
        mock_pc_instance = MagicMock()
        mock_pc_instance.Index.return_value = MagicMock()
        mock_pc_class.return_value = mock_pc_instance
        yield mock_pc_class
