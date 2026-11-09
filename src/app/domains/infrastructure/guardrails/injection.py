"""Prompt-injection guard — high-precision regex signals.

False positives are worse than false negatives here (we BLOCK on hit), so the
patterns are deliberately conservative: only unambiguous adversarial phrasing.

Common bypasses (encoding, leetspeak, indirect injection) are NOT caught by
regex — add an LLM-based guard later as an opt-in second pass if you need it.
"""

import re
from typing import Optional

from app.domains.interfaces.guardrail import BaseGuard, GuardResult

_SIGNALS: list[re.Pattern] = [
    re.compile(r"ignore\s+(?:all\s+)?(?:previous|prior)\s+instructions?", re.I),
    re.compile(
        r"disregard\s+(?:all\s+)?(?:previous|prior|the)\s+(?:instructions|prompts?|rules)",
        re.I,
    ),
    re.compile(r"you\s+are\s+now\s+(?:a|an)\s+", re.I),
    re.compile(r"(?:^|\s)(?:act|pretend|play)\s+as\s+(?:if\s+you\s+(?:are|were)\s+)?", re.I),
    re.compile(r"system\s*:\s*", re.I),
    # ChatML / special-token injection
    re.compile(r"<\s*\|?(?:system|im_start|im_end)\|?\s*>", re.I),
    # Direct prompt-extraction attempts
    re.compile(
        r"\b(?:reveal|show|print|output|repeat|recite)\s+(?:your|the)\s+(?:system\s+)?(?:prompt|instructions?|rules)",
        re.I,
    ),
    re.compile(r"\bDAN\b\s+mode", re.I),
    re.compile(r"jailbreak", re.I),
    # Role spoofing at line start
    re.compile(r"(?:^|\n)\s*(?:USER|ASSISTANT|SYSTEM)\s*:", re.I),
]


class PromptInjectionGuard(BaseGuard):
    name = "prompt_injection"
    stage = "input"

    def check(self, text: str, context: Optional[dict] = None) -> GuardResult:
        hits: dict[str, int] = {}
        for pat in _SIGNALS:
            found = pat.findall(text)
            if found:
                hits[pat.pattern] = len(found)
        if not hits:
            return GuardResult(outcome="allowed")
        return GuardResult(
            outcome="blocked",
            reason="Potential prompt injection detected",
            scores={"matched_patterns": hits},
            snippet=text[:200],
        )
