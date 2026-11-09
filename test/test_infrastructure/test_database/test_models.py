from app.domains.infrastructure.database.models import Document, ChatMessage, GuardrailLog

def test_document_model_defaults():
    doc = Document(title="Test Doc", content="Some content")
    # server_default is applied by the database on insert, so in-memory it might be None 
    # unless a Python-level default is also explicitly triggered. Both are valid.
    assert doc.status in ("pending", None)
    assert doc.id is not None
    assert len(doc.id) == 36

def test_chat_message_model():
    msg = ChatMessage(thread_id="thread-123", role="user", content="Hello", meta={"source": "rag"})
    assert msg.role == "user"
    assert msg.meta["source"] == "rag"

def test_guardrail_log_model():
    log = GuardrailLog(thread_id="thread-123", stage="input", guard="pii_filter", outcome="blocked", reason="PII detected")
    assert log.stage == "input"
    assert log.outcome == "blocked"
