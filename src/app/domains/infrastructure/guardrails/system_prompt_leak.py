"""System-prompt-leak guard (output) — block if the model echoes its instructions."""

from typing import Optional

from app.domains.interfaces.guardrail import BaseGuard, GuardResult

# Phrases that strongly suggest the model is parroting its system prompt
# instead of answering the question.
_LEAK_MARKERS: list[str] = [
    "you are a helpful assistant",
    "your instructions are",
    "system prompt",
    "I was instructed to",
    "my guidelines say",
    "as an AI language model, I cannot",  # also catches lazy refusals
]


class SystemPromptLeakGuard(BaseGuard):
    name = "system_prompt_leak"
    stage = "output"

    def __init__(self, markers: Optional[list[str]] = None) -> None:
        self._markers = [m.lower() for m in (markers or _LEAK_MARKERS)]

    def check(self, text: str, context: Optional[dict] = None) -> GuardResult:
        lower = text.lower()
        hits = [m for m in self._markers if m in lower]
        if not hits:
            return GuardResult(outcome="allowed")
        return GuardResult(
            outcome="blocked",
            reason="Possible system prompt leakage in output",
            scores={"matched": hits},
            snippet=text[:200],
        )
