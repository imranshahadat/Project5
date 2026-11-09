#!/usr/bin/env python3
"""Interactive terminal chat for the RAG pipeline.

Talks to your REAL infrastructure — LLM, embeddings, Pinecone, Postgres —
so your .env must be fully configured.

Usage:
    python scripts/chat_terminal.py
    python scripts/chat_terminal.py --thread my-conversation
    python scripts/chat_terminal.py --tenant acme --user alice --admin

In-chat commands:
    /new            start a new conversation thread
    /thread <id>    switch to / resume an existing thread
    /sources        show last turn's source documents
    /guards         show last turn's guardrail outcomes
    /raw            show the full last result as JSON
    /help           show commands
    /quit           exit
"""

import argparse
import json
import logging
import os
import sys
import uuid

# --- bootstrap sys.path so `from app...` resolves regardless of cwd ---
# matches the layout the smoke test uses.
_HERE = os.path.dirname(os.path.abspath(__file__))
_PARENT = os.path.dirname(_HERE)
for _candidate in (_PARENT, os.path.join(_PARENT, "src")):
    if os.path.isdir(os.path.join(_candidate, "app")):
        sys.path.insert(0, _candidate)
        break

from app.application.services.chat import chat  # noqa: E402
from app.core.exceptions import AppError  # noqa: E402
from app.domains.interfaces.access import Principal  # noqa: E402


# ---------- minimal ANSI colours (disabled on non-TTY) ----------
_USE_COLOR = sys.stdout.isatty()


class C:
    RESET = "\033[0m" if _USE_COLOR else ""
    BOLD = "\033[1m" if _USE_COLOR else ""
    DIM = "\033[2m" if _USE_COLOR else ""
    GREEN = "\033[32m" if _USE_COLOR else ""
    YELLOW = "\033[33m" if _USE_COLOR else ""
    RED = "\033[31m" if _USE_COLOR else ""
    CYAN = "\033[36m" if _USE_COLOR else ""
    MAGENTA = "\033[35m" if _USE_COLOR else ""


# ---------- display helpers ----------

_STATUS_COLOR = {
    "answered": C.GREEN,
    "no_evidence": C.YELLOW,
    "blocked": C.RED,
}


def _print_answer(result: dict) -> None:
    status = result.get("status", "answered")
    sc = _STATUS_COLOR.get(status, "")

    print(f"\n{C.BOLD}Answer:{C.RESET} {result.get('answer', '')}\n")
    print(f"{sc}{C.BOLD}Status:{C.RESET} {status}")

    sources = result.get("sources") or []
    if sources:
        print(f"\n{C.CYAN}Sources ({len(sources)}):{C.RESET}")
        for i, s in enumerate(sources, 1):
            score = s.get("score", 0.0)
            print(
                f"  [{i}] {s.get('title', 'untitled')}  "
                f"{C.DIM}doc={s.get('doc_id', '?')} chunk={s.get('chunk_index', '?')} "
                f"score={score:.3f}{C.RESET}"
            )
    else:
        print(f"{C.DIM}No sources.{C.RESET}")

    guards = result.get("guardrail_outcomes") or []
    interesting = [g for g in guards if g.get("outcome") != "allowed"]
    if interesting:
        print(f"\n{C.MAGENTA}Guardrails (non-allowed):{C.RESET}")
        for g in interesting:
            print(
                f"  [{g['stage']}] {g['guard']}: {g['outcome']}"
                + (f" — {g['reason']}" if g.get("reason") else "")
            )
    print()


def _print_raw(result: dict) -> None:
    print(f"\n{C.DIM}{json.dumps(result, indent=2, default=str)}{C.RESET}\n")


# ---------- REPL ----------

HELP_TEXT = f"""
{C.BOLD}Commands:{C.RESET}
  /new            start a new conversation thread
  /thread <id>    switch to / resume an existing thread
  /sources        show last turn's source documents
  /guards         show last turn's guardrail outcomes
  /raw            show the full last result as JSON
  /help           show this help
  /quit           exit

{C.BOLD}Tips:{C.RESET}
  {C.DIM}- Follow-up questions work: chat history is loaded per thread.{C.RESET}
  {C.DIM}- Multi-line not supported; press Enter to send.{C.RESET}
  {C.DIM}- Errors are logged to stderr; the pipeline never crashes on a bad question.{C.RESET}
"""


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Interactive RAG chat terminal",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--thread",
        default=None,
        help="thread ID (auto-generated if omitted)",
    )
    parser.add_argument("--tenant", default="public", help="tenant ID for access filter")
    parser.add_argument("--user", default="terminal-user", help="subject / user ID")
    parser.add_argument(
        "--admin",
        action="store_true",
        help="bypass the tenant/group/subject access filter (see all docs)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="show INFO logs from the pipeline (retrieval counts, etc.)",
    )
    args = parser.parse_args()

    # --- logging ---
    level = logging.INFO if args.verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-5s %(name)s: %(message)s",
        stream=sys.stderr,
    )

    # --- principal ---
    principal = Principal(
        tenant_id=args.tenant,
        subject_id=args.user,
        is_admin=args.admin,
    )

    thread_id = args.thread or f"term-{uuid.uuid4().hex[:8]}"

    # --- banner ---
    print(f"{C.BOLD}{'=' * 50}{C.RESET}")
    print(f"{C.BOLD}  RAG Chat Terminal{C.RESET}")
    print(f"{'=' * 50}")
    print(f"  Thread : {C.CYAN}{thread_id}{C.RESET}")
    print(f"  User   : {args.user}")
    print(f"  Tenant : {args.tenant}  admin={args.admin}")
    print(f"{C.DIM}  Type /help for commands, /quit to exit.{C.RESET}\n")

    last_result: dict | None = None

    while True:
        try:
            question = input(f"{C.BOLD}you>{C.RESET} ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{C.DIM}bye.{C.RESET}")
            return 0

        if not question:
            continue

        # --- slash commands ---
        if question.startswith("/"):
            cmd, _, rest = question.partition(" ")
            cmd = cmd.lower()

            if cmd in ("/quit", "/exit", "/q"):
                print(f"{C.DIM}bye.{C.RESET}")
                return 0

            if cmd == "/new":
                thread_id = f"term-{uuid.uuid4().hex[:8]}"
                last_result = None
                print(f"{C.GREEN}New thread: {thread_id}{C.RESET}\n")
                continue

            if cmd == "/thread":
                new_id = rest.strip()
                if not new_id:
                    print(f"{C.YELLOW}Usage: /thread <id>{C.RESET}\n")
                    continue
                thread_id = new_id
                last_result = None
                print(f"{C.GREEN}Switched to thread: {thread_id}{C.RESET}\n")
                continue

            if cmd == "/sources":
                if last_result and last_result.get("sources"):
                    for s in last_result["sources"]:
                        print(f"  {s}")
                else:
                    print(f"{C.DIM}No sources from last turn.{C.RESET}")
                print()
                continue

            if cmd == "/guards":
                if last_result and last_result.get("guardrail_outcomes"):
                    for g in last_result["guardrail_outcomes"]:
                        print(
                            f"  [{g['stage']}] {g['guard']}: {g['outcome']}"
                            + (f" — {g.get('reason','')}" if g.get("reason") else "")
                        )
                else:
                    print(f"{C.DIM}No guardrail outcomes.{C.RESET}")
                print()
                continue

            if cmd == "/raw":
                if last_result:
                    _print_raw(last_result)
                else:
                    print(f"{C.DIM}No result yet.{C.RESET}\n")
                continue

            if cmd == "/help":
                print(HELP_TEXT)
                continue

            print(f"{C.YELLOW}Unknown command: {cmd}. Type /help.{C.RESET}\n")
            continue

        # --- run the pipeline ---
        try:
            result = chat(principal, question, thread_id=thread_id)
            last_result = result
            _print_answer(result)
        except AppError as e:
            # app-level errors: config missing, API keys, provider init, etc.
            print(f"\n{C.RED}Config / provider error:{C.RESET} {e}\n")
            print(
                f"{C.DIM}Check your .env — common causes: missing API keys, "
                f"DATABASE_URL, or PINECONE_INDEX_NAME.{C.RESET}\n"
            )
        except Exception as e:
            print(f"\n{C.RED}Unexpected error:{C.RESET} {e}\n")
            logging.getLogger("chat_terminal").exception("chat() failed")


if __name__ == "__main__":
    sys.exit(main())
