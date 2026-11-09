from app.domains.infrastructure.guardrails.pii import PIIInputGuard, PIIOutputGuard

def test_pii_input_guard_redact_mode():
    guard = PIIInputGuard(block=False)
    result = guard.check("Contact me at test@example.com or 555-123-4567.")
    assert result.outcome == "redacted"
    assert "test@example.com" not in result.redacted_text
    assert "[REDACTED]" in result.redacted_text

def test_pii_input_guard_block_mode():
    guard = PIIInputGuard(block=True)
    result = guard.check("My SSN is 123-45-6789.")
    assert result.outcome == "blocked"
    # The guard outputs the key in lowercase ('ssn'), so we check for that or the general message
    assert "PII detected" in result.reason
    assert "ssn" in result.reason

def test_pii_output_guard_blocks_by_default():
    guard = PIIOutputGuard(block=True)
    result = guard.check("Here is the card number: 4111 1111 1111 1111")
    assert result.outcome == "blocked"
    assert result.scores["counts"]["card"] == 1

def test_pii_guard_no_pii_found():
    guard = PIIInputGuard(block=False)
    assert guard.check("This is a completely safe sentence.").outcome == "allowed"
