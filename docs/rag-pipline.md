# RAG Chat Pipeline — Implementation Summary

## What was built

A LangGraph-orchestrated RAG chat pipeline that follows the provided flow diagram exactly: input guardrails → retrieval (with access control) → conditional routing → generation or no-evidence → output guardrails → result. Guardrails run in parallel with zero LLM calls (pure regex/keyword), designed so new guards can be added without touching the graph.

---

## Architecture

```
START → guard → (blocked?) ──yes──→ END  [status=blocked]
              │
              no
              ↓
          retrieve → (passages?) ──no──→ no_evidence → END  [status=no_evidence]
              │
              yes
              ↓
          generate → validate → END  [status=answered]
```

Built on the existing hexagonal (ports-and-adapters) architecture:
- **Ports** (`app/domains/interfaces/`) — vendor-neutral ABCs
- **Adapters** (`app/domains/infrastructure/`) — concrete implementations
- **Composition root** (`app/application/dependencies/providers.py`) — the only place adapters are built
- **Application services** (`app/application/services/`) — orchestration logic

---

## Files created

### Ports (new interfaces)

| File | Purpose |
|---|---|
| `app/domains/interfaces/guardrail.py` | `BaseGuard` + `GuardResult` dataclass |
| `app/domains/interfaces/guardrail_log.py` | `BaseGuardrailLogRepository` |
| `app/domains/interfaces/access.py` | `Principal` dataclass + `BaseAccessFilterBuilder` |
| `app/domains/interfaces/chat_history.py` | `BaseChatHistoryRepository` |

### Guardrail infrastructure

| File | Purpose |
|---|---|
| `app/domains/infrastructure/guardrails/runner.py` | Parallel executor (`ThreadPoolExecutor`) |
| `app/domains/infrastructure/guardrails/pii.py` | PII input (redact) + output (block) guards |
| `app/domains/infrastructure/guardrails/injection.py` | Prompt injection detector |
| `app/domains/infrastructure/guardrails/toxicity.py` | Banned-language keyword filter |
| `app/domains/infrastructure/guardrails/system_prompt_leak.py` | Output leak detector |
| `app/domains/infrastructure/guardrails/factory.py` | Builds guard chains from config |

### Access control + repositories

| File | Purpose |
|---|---|
| `app/domains/infrastructure/access/tenant_filter.py` | Pinecone `$or` filter from Principal |
| `app/domains/infrastructure/database/postgres_chat_history.py` | ChatMessage repository (auto-detects `meta` vs `metadata` attr) |
| `app/domains/infrastructure/database/postgres_guardrail_log.py` | GuardrailLog repository |

### LangGraph nodes + orchestration

| File | Purpose |
|---|---|
| `app/application/services/chat_state.py` | `ChatState` TypedDict + `ChatResult` |
| `app/application/services/query_rewriter.py` | Follow-up query rewrite (1 LLM call, history-aware) |
| `app/application/services/chat.py` | `chat()` entry point + `build_chat_graph()` |
| `app/application/services/nodes/routing.py` | `route_after_guard`, `route_after_retrieve` |
| `app/application/services/nodes/guard.py` | GUARD node — input guardrails |
| `app/application/services/nodes/retrieve.py` | RETRIEVE node — history, embed, search, threshold |
| `app/application/services/nodes/generate.py` | GENERATE node — evidence + LLM call |
| `app/application/services/nodes/no_evidence.py` | NO_EVIDENCE node — static message |
| `app/application/services/nodes/validate.py` | VALIDATE node — output guardrails |

### Scripts

| File | Purpose |
|---|---|
| `scripts/test_chat_smoke.py` | End-to-end smoke test (5 scenarios, mocked providers) |
| `scripts/chat_terminal.py` | Interactive terminal chat client |
| `scripts/diagnose_models.py` | Dumps GuardrailLog + ChatMessage column names |

---

## Files modified

### `app/core/config.py`
Added three settings blocks:
- **`ChatSettings`** — history_turns, rewrite_followup, max_answer_chars, no_evidence_message
- **`GuardrailSettings`** — enabled, parallel, input_guards (CSV), output_guards (CSV), pii_block_input/output, toxicity_banned_words
- **`AccessControlSettings`** — enabled (default false, opt-in)

### `app/application/dependencies/providers.py`
- Added `build_access_filter()`, `build_chat_history_repository()`, `build_guardrail_log_repository()`
- Re-exported `build_input_guards` / `build_output_guards` from the guardrails factory
- **Bug fixes:**
  - Removed duplicate `get_vector_store()` (NotImplementedError stub was shadowing the real one)
  - Consolidated duplicate `reset_all_caches()` (the testing-helper version omitted `get_storage`)
  - Removed duplicate `PostgresDocumentRepository` import
  - Removed `@lru_cache` from `build_*_repository(session)` functions (caching on Session objects is a leak)

---

## Cost and latency profile

| Component | LLM calls | Cost | Notes |
|---|---|---|---|
| Input guardrails (PII + injection + toxicity) | 0 | free | Pure regex/keyword, run in parallel |
| Query rewrite | 0–1 | 1 cheap call | Only if chat history exists; skipped on first turn |
| Embedding | 1 | cheap | `embed_query()` |
| Vector search | 0 | Pinecone call | |
| Generate | 1 | main call | The only always-on LLM call |
| Output guardrails (PII + system-prompt-leak) | 0 | free | Pure regex, run in parallel |
| **Total per question** | **1–2** | | |

Parallel guard execution uses `ThreadPoolExecutor` — today's regex guards finish in milliseconds, and the design future-proofs for LLM-based guards (total latency = max, not sum).

---

## Extending guardrails

Adding a new guard requires no graph or node changes:

1. Create `app/domains/infrastructure/guardrails/myguard.py` with a class extending `BaseGuard`
2. Add one entry to `_INPUT_FACTORIES` or `_OUTPUT_FACTORIES` in `guardrails/factory.py`
3. Add the guard name to `INPUT_GUARDS` or `OUTPUT_GUARDS` in `.env`

The runner executes it in parallel with existing guards automatically.

---

## .env additions

```env
# Guardrails
GUARDRAILS_ENABLED=true
GUARDRAILS_PARALLEL=true
INPUT_GUARDS=pii,injection,toxicity
OUTPUT_GUARDS=pii,system_prompt_leak
PII_BLOCK_INPUT=false
PII_BLOCK_OUTPUT=true
TOXICITY_BANNED_WORDS=

# Chat
CHAT_HISTORY_TURNS=6
CHAT_REWRITE_FOLLOWUP=true
CHAT_MAX_ANSWER_CHARS=2000
CHAT_NO_EVIDENCE_MSG=I could not find supporting evidence in the available documents.

# Access control (off until ingestion tags chunks with tenant_id)
ACCESS_CONTROL_ENABLED=false
```

---

## How to run

### Smoke test (mocked providers, no external deps needed)

```bash
python scripts/test_chat_smoke.py
```

Verifies: happy path, no-evidence routing, blocked input, PII redaction, parallel guard execution.

### Terminal chat (real infrastructure)

```bash
python scripts/chat_terminal.py
python scripts/chat_terminal.py --thread my-conversation
python scripts/chat_terminal.py --tenant acme --user alice --admin
python scripts/chat_terminal.py --verbose
```

In-chat commands: `/new`, `/thread <id>`, `/sources`, `/guards`, `/raw`, `/help`, `/quit`

Requires `.env` with `VERCEL_API_KEY`, `PINECONE_API_KEY`, `PINECONE_INDEX_NAME`, `DATABASE_URL`.

---

## Fixes applied during integration

### `postgres_chat_history.py` — metadata attribute auto-detection

The pasted `models.py` used `meta` as the Python attribute (with DB column `metadata`), but the user's actual model uses `metadata` directly. The repository now auto-detects:

```python
_COLUMN_ATTRS = set(ChatMessage.__mapper__.column_attrs.keys())
_META_ATTR = "meta" if "meta" in _COLUMN_ATTRS else "metadata"
```

Works with both layouts without code changes.

### Database migration needed

The `guardrail_logs` table must have a `guard` column matching the model. If missing:

```sql
ALTER TABLE guardrail_logs ADD COLUMN IF NOT EXISTS guard VARCHAR(64);
```

### Pinecone client upgrade

If the Pinecone index uses a document schema, the `pinecone` package must be upgraded:

```bash
pip install --upgrade pinecone
```

The adapter at `app/domains/infrastructure/vector_store/pinecone.py` may need to switch from the vectors API (`index.query()`) to the documents API if the upgraded client doesn't auto-route.

---

## Tracing

LangGraph auto-traces every node when `LANGCHAIN_TRACING_V2=true` and `LANGCHAIN_API_KEY` are set in `.env`. Each node appears in LangSmith with its node name — satisfying the `@trace("...")` annotations in the flow diagram with no extra decorators.

---

## What's NOT wired yet

- **Access control** — `ACCESS_CONTROL_ENABLED=false` by default. Ingestion (`app/application/services/ingestion.py`) must tag chunks with `tenant_id` metadata before enabling.
- **HITL approvals** — the `approvals` table exists in the model but no approval flow is implemented.
- **Feedback** — the `feedback` table exists but no feedback collection is implemented.
- **Reranker** — `RetrievalSettings.use_reranker` and `reranker_model` exist but the retrieve node doesn't call a reranker yet.