import pytest
from unittest.mock import patch, MagicMock
from app.domains.infrastructure.extractors.pypdf import PypdfTextExtractor

def test_pypdf_extractor_success():
    extractor = PypdfTextExtractor()
    mock_reader = MagicMock()
    mock_reader.pages = [MagicMock(extract_text=MagicMock(return_value="Page 1")), MagicMock(extract_text=MagicMock(return_value="Page 2"))]
    with patch("app.domains.infrastructure.extractors.pypdf.PdfReader", return_value=mock_reader):
        assert extractor.extract(b"fake_pdf", "test.pdf") == "Page 1\n\nPage 2"

def test_pypdf_extractor_empty_page():
    extractor = PypdfTextExtractor()
    mock_reader = MagicMock()
    mock_reader.pages = [MagicMock(extract_text=MagicMock(return_value=None))]
    with patch("app.domains.infrastructure.extractors.pypdf.PdfReader", return_value=mock_reader):
        assert extractor.extract(b"fake_pdf", "test.pdf") == ""
