from app.domains.infrastructure.guardrails.toxicity import ToxicityGuard

def test_toxicity_guard_allows_clean_text():
    guard = ToxicityGuard(banned_words={"badword", "spam"})
    assert guard.check("This is a perfectly nice message.").outcome == "allowed"

def test_toxicity_guard_blocks_banned_words():
    guard = ToxicityGuard(banned_words={"badword", "spam"})
    result = guard.check("This message contains BADWORD and some spam.")
    assert result.outcome == "blocked"
    assert result.scores["count"] == 2

def test_toxicity_guard_no_op_when_empty():
    guard = ToxicityGuard(banned_words=None)
    assert guard.check("This contains badword but guard is not configured.").outcome == "allowed"
