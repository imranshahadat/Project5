"""Build the input/output guard chains from settings.

Adding a new guard = one entry in ``_INPUT_FACTORIES`` / ``_OUTPUT_FACTORIES``
and (optionally) a new env var. The graph, runner, and logging all stay the same.
"""

from typing import Callable, Optional

from app.core.config import AppSettings, get_settings
from app.domains.interfaces.guardrail import BaseGuard
from app.domains.infrastructure.guardrails.injection import PromptInjectionGuard
from app.domains.infrastructure.guardrails.pii import PIIInputGuard, PIIOutputGuard
from app.domains.infrastructure.guardrails.system_prompt_leak import (
    SystemPromptLeakGuard,
)
from app.domains.infrastructure.guardrails.toxicity import ToxicityGuard

_InputFactory = Callable[[AppSettings], BaseGuard]
_OutputFactory = Callable[[AppSettings], BaseGuard]

_INPUT_FACTORIES: dict[str, _InputFactory] = {
    "pii": lambda s: PIIInputGuard(block=s.guardrails.pii_block_input),
    "injection": lambda _s: PromptInjectionGuard(),
    "toxicity": lambda s: ToxicityGuard(
        banned_words=_parse_csv_set(s.guardrails.toxicity_banned_words)
    ),
}

_OUTPUT_FACTORIES: dict[str, _OutputFactory] = {
    "pii": lambda s: PIIOutputGuard(block=s.guardrails.pii_block_output),
    "system_prompt_leak": lambda _s: SystemPromptLeakGuard(),
}


def _parse_csv_list(csv: str) -> list[str]:
    return [x.strip() for x in csv.split(",") if x.strip()]


def _parse_csv_set(csv: str) -> set[str]:
    return set(_parse_csv_list(csv))


def build_input_guards(settings: Optional[AppSettings] = None) -> list[BaseGuard]:
    s = settings or get_settings()
    if not s.guardrails.enabled:
        return []
    names = _parse_csv_list(s.guardrails.input_guards)
    guards: list[BaseGuard] = []
    for n in names:
        factory = _INPUT_FACTORIES.get(n)
        if factory:
            guards.append(factory(s))
    return guards


def build_output_guards(settings: Optional[AppSettings] = None) -> list[BaseGuard]:
    s = settings or get_settings()
    if not s.guardrails.enabled:
        return []
    names = _parse_csv_list(s.guardrails.output_guards)
    guards: list[BaseGuard] = []
    for n in names:
        factory = _OUTPUT_FACTORIES.get(n)
        if factory:
            guards.append(factory(s))
    return guards
