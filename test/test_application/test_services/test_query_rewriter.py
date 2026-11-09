import pytest
from unittest.mock import patch, MagicMock
from app.application.services.query_rewriter import rewrite_followup_query

def test_rewrite_followup_no_history():
    assert rewrite_followup_query("What is the capital of France?", []) == "What is the capital of France?"

@patch("app.application.services.query_rewriter.get_llm")
def test_rewrite_followup_success(mock_get_llm):
    mock_get_llm.return_value.generate.return_value = "  Capital of France?  "
    history = [{"role": "user", "content": "Tell me about France."}]
    assert rewrite_followup_query("What is its capital?", history) == "Capital of France?"

@patch("app.application.services.query_rewriter.get_llm")
def test_rewrite_followup_fallback_on_exception(mock_get_llm):
    mock_get_llm.side_effect = Exception("Network error")
    assert rewrite_followup_query("Follow up question", [{"role": "user", "content": "Context"}]) == "Follow up question"

@patch("app.application.services.query_rewriter.get_llm")
def test_rewrite_followup_fallback_on_too_long(mock_get_llm):
    mock_get_llm.return_value.generate.return_value = "A" * 600
    assert rewrite_followup_query("Short question", [{"role": "user", "content": "Context"}]) == "Short question"
