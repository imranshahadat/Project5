"""Run a list of guards — sequentially or in parallel.

Parallel uses a thread pool: perfect for the regex/keyword guards we ship today
(CPU-light, no I/O) and **future-proofs** the design — when you add an LLM-based
or remote-API guard later, it's already running in parallel at no extra latency.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

from app.domains.interfaces.guardrail import BaseGuard, GuardResult


def run_guards(
    guards: list[BaseGuard],
    text: str,
    *,
    parallel: bool = True,
    context: Optional[dict] = None,
) -> list[tuple[str, GuardResult]]:
    """Run every guard against `text`.

    Returns ``[(guard_name, GuardResult), ...]`` in **registration order**
    (so logs are deterministic regardless of which guard finishes first).
    """
    if not guards:
        return []

    if not parallel or len(guards) == 1:
        return [(g.name, g.check(text, context)) for g in guards]

    results: dict[str, GuardResult] = {}
    # Cap workers — guard count is small (3-6 typically); more threads = waste.
    max_workers = min(len(guards), 8)
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        future_to_name = {
            ex.submit(g.check, text, context): g.name for g in guards
        }
        for fut in as_completed(future_to_name):
            name = future_to_name[fut]
            results[name] = fut.result()  # propagate exceptions — fail fast

    # Preserve registration order so logs/readouts are stable.
    return [(g.name, results[g.name]) for g in guards]
