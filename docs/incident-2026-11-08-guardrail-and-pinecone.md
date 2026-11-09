
# Incident Report & Fix Log — Guardrail Persistence + Pinecone Index Schema

| | |
|---|---|
| **Project** | Project4 — RAG chat terminal (LangGraph + Pinecone + PostgreSQL + S3 + Vercel AI Gateway) |
| **Date** | 2026-11-08 |
| **Environment** | Ubuntu (imran-Latitude-E7250), Python 3.14 venv, `pinecone` SDK 10.3.0, SQLAlchemy 2.x, pydantic-settings |
| **Outcome** | ✅ All errors resolved — S3, Pinecone, guardrail persistence, and the full chat graph verified green |

---

## 1. TL;DR

| # | Symptom | Root cause | Fix | Status |
|---|---------|-----------|-----|--------|
| 1 | `TypeError: 'guard' is an invalid keyword argument for GuardrailLog` (logged as non-fatal) | Name drift: port/repo/callers use `guard`, SQLAlchemy model column was `guardrail`. Same drift existed in the DDL as a leftover `ALTER TABLE ... ADD COLUMN guard`. | Model attribute renamed to `guard`, mapped to the unchanged DB column: `mapped_column("guardrail", String(64))` | ✅ Fixed |
| 2 | Pinecone `[400] This index has a document schema, so reads must go through the documents API` | Index was created as a **document-schema / integrated-embedding index** (likely console quickstart). The app embeds client-side and uses the vectors API — incompatible. | Deleted the (empty) index, recreated a **plain dense index** (1024 dims, cosine) | ✅ Fixed |
| 3 | Pinecone `[404 NOT_FOUND] Resource cloud: aws region: aped-27b4-a not found` during recreate | Invalid `PINECONE_REGION` in `.env` (never mattered before — old index was made in the console) | `PINECONE_REGION=us-east-1` in `.env` | ✅ Fixed |
| 4 | Smoke test `[404 NOT_FOUND] Resource rag-knowledge-base4627b74apinecone not found` | **Expected** — index had been deleted, create (step above) had failed, so nothing existed | Resolved automatically by fix #3 + recreate | ✅ Resolved |
| 5 | Chat answers `"Status: no_evidence"` | **Not a bug** — index was empty after recreation; nothing to retrieve | Ingest a document (one-off script below); watch `SIMILARITY_THRESHOLD` for cohere models | ✅ Understood |

---

## 2. System context

```
Ingestion:  upload ──> S3 ──> process_s3_key(key)
                              ├─ documents row lookup (status pending/failed only)
                              ├─ download from S3, validate ext (pdf|docx|txt/md)
                              ├─ extract text → chunk (size/overlap)
                              ├─ embed (cohere/embed-v4.0 via Vercel AI Gateway, 1024 dims)
                              ├─ delete_by_filter(doc_id) + upsert → Pinecone
                              └─ status=ready + audit row

Chat:       question ──> GUARD (input guardrails, parallel, persist to guardrail_logs)
                     ──> RETRIEVE (history → rewrite → embed → vector search → threshold)
                     ──> GENERATE / NO_EVIDENCE ──> VALIDATE (output guardrails)
```

Architecture: ports & adapters (`BaseVectorStore`, `BaseEmbeddings`, `BaseGuardrailLogRepository`, …) with a composition root in `app/application/dependencies/providers.py`. The app **embeds client-side** and talks to Pinecone with the **vectors API** (`/vectors/upsert`, `/query`).

Key config (from `src/app/core/config.py` + `.env`):
- `EMBEDDING_MODEL=cohere/embed-v4.0`, `EMBEDDING_DIMENSIONS=1024`
- `PINECONE_INDEX_NAME=rag-knowledge-base4627b74apinecone`, metric `cosine`, dimension 1024
- `SIMILARITY_THRESHOLD=0.70`, `DEFAULT_RETRIEVAL_K=4`

---

## 3. Error 1 — `TypeError: 'guard' is an invalid keyword argument for GuardrailLog`

### 3.1 Symptom

Every chat turn logged (then swallowed as non-fatal):

```
ERROR app.application.services.nodes.guard: Failed to persist input guardrail logs (non-fatal)
  File ".../postgres_guardrail_log.py", line 27, in append
    GuardrailLog(
TypeError: 'guard' is an invalid keyword argument for GuardrailLog
```

Consequence: chat kept working, but the `guardrail_logs` audit table stayed **silently empty** — no trace of blocked/flagged/redacted events.

### 3.2 Investigation

Traced the full call chain:

```
guard.py (_persist_outcomes)          → repo.append(..., guard=o["guard"], ...)
interfaces/guardrail_log.py (port)    → append(*, guard: str, ...)          # "guard"
postgres_guardrail_log.py (repo)      → GuardrailLog(guard=guard, ...)       # "guard"
database/models.py (SQLAlchemy model) → guardrail: Mapped[str] = mapped_column(String(64))  # "guardrail"  ← MISMATCH
db/reference_schema.sql               → guardrail VARCHAR(64) NOT NULL       # column is "guardrail"
```

Everything above the model agreed on `guard`; the model and DB used `guardrail`.

**Root cause:** a historical column rename (`guard` → `guardrail`) was applied to the DDL and model, but (a) the DDL kept a leftover migration line, and (b) the repo layer kept using the old name. The app's own rule — *"models are the source of truth; keep `reference_schema.sql` in sync"* — had drifted in two places.

### 3.3 Related DDL fix (`db/reference_schema.sql`)

Two defects found and fixed in the same review:

1. **Dead migration left in the reference DDL** (would create schema drift on fresh bootstraps):
   ```sql
   -- REMOVED: leftover from the guard → guardrail rename
   ALTER TABLE guardrail_logs ADD COLUMN IF NOT EXISTS guard VARCHAR(64);
   ```
2. **Mangled formatting in the `feedback` table** (`ON DELETE SET NULL` split across a line break with broken indentation). Cosmetically fixed:
   ```sql
   message_id VARCHAR(36) REFERENCES chat_history (id) ON DELETE SET NULL,
   ```

Optional cleanup for any live DB bootstrapped from the old DDL:

```sql
ALTER TABLE guardrail_logs DROP COLUMN IF EXISTS guard;
```

### 3.4 Fix (one line, in `src/app/domains/infrastructure/database/models.py`)

Keep the DB column and DDL untouched; rename only the **ORM attribute** so the whole code chain agrees:

```python
class GuardrailLog(Base):
    __tablename__ = "guardrail_logs"
    ...
    # attribute is `guard` (matches port + repo), DB column stays `guardrail`
    guard: Mapped[str] = mapped_column("guardrail", String(64))  # e.g. "pii_filter"
```

`guard.py`, `postgres_guardrail_log.py`, the interface, and the database schema all need **zero changes**.

### 3.5 Verification

```bash
# mapping check
PYTHONPATH=src .venv/bin/python -c "
from app.domains.infrastructure.database.models import GuardrailLog
for c in GuardrailLog.__table__.columns:
    if c.key == 'guard':
        print('attr:', c.key, '-> column:', c.name)
"   # expect: attr: guard -> column: guardrail

# end-to-end insert
PYTHONPATH=src .venv/bin/python -c "
from app.application.dependencies.providers import get_db_session, build_guardrail_log_repository
with get_db_session() as s:
    build_guardrail_log_repository(s).append(thread_id='smoke-guard', stage='input',
        guard='pii_filter', outcome='allowed', reason=None, snippet=None, scores=None)
print('guardrail append OK')
"
# → guardrail append OK ✅

# audit trail now filling up
psql "$DATABASE_URL" -c "SELECT stage, guardrail, outcome, thread_id, created_at FROM guardrail_logs ORDER BY created_at DESC LIMIT 5;"
```

> **First attempt failed** — the edit had not actually landed in the file (identical traceback). Lesson: verify edits mechanically (`grep -n` before/after `sed`), don't trust "I changed it". Also two known failure modes were pre-planned for: stale `__pycache__` (`find src -name __pycache__ -type d -exec rm -rf {} +`) and a missing column (`ALTER TABLE guardrail_logs ADD COLUMN IF NOT EXISTS guardrail VARCHAR(64);`).

---

## 4. Error 2 — Pinecone `[400] This index has a document schema…`

### 4.1 Symptom (reads — first seen in chat)

```
pinecone.errors.exceptions.ApiError: [400] This index has a document schema, so reads must go
through the documents API. Use POST /namespaces/{namespace}/documents/search, /fetch or /list
with the X-Pinecone-API-Version header set to 2026-07 or later. The vectors and records read
endpoints do not support document schemas. ...
```

Crashed in `retrieve_node → PineconeVectorStore.query → index.query(vector=...)`. This killed the whole chat turn.

### 4.2 Diagnosis steps

1. **Reads blocked** — confirmed by the chat traceback (vectors-API read).
2. **Writes blocked too** — the project smoke test (`scripts/smoke_vector_and_s3.py`) proved it:
   - S3 roundtrip: ✅ (`put`/`get`/`presigned_url`/`delete`)
   - `stats()`: ✅ — `dimension: 1024, metric: cosine, vector_type: dense, total_vector_count: 0`
   - `upsert(ids, vectors, metadatas)`: ❌ `[400] … writes must go through the documents API. Use POST /namespaces/{namespace}/documents/upsert …`
3. **Index type check**: `pc.describe_index(...)` reported dims 1024 / cosine, but SDK 10.3.0 did **not** expose an `embed`/schema field (`getattr(d, 'embed', None) → None` — inconclusive). The authoritative evidence was the 400 error text itself.
4. **Embedding dimension check**: `len(get_embeddings().embed_query("dimension check")) == 1024` ✅ — matches `PINECONE_DIMENSION`.

**Root cause:** the index had been created as an integrated-embedding / document-schema index (most likely via the Pinecone console quickstart). That index class only accepts the **documents API** for reads *and* writes; the application's entire design (client-side embeddings + vectors API) is incompatible with it. Upgrading the SDK could not fix this — the API surface itself is different.

### 4.3 Decision: Option A vs Option B

| | Option A — plain dense index | Option B — documents API / integrated embeddings |
|---|---|---|
| Code changes | **None** (adapter untouched) | Store interface changes (`query(vector=)` → `query(text=)`), ingestion → `upsert_records`, response mapping → `result.hits[].fields` |
| Embeddings | Client-side (cohere/embed-v4.0 via Vercel gateway) | Server-side (index-owned model) |
| Fits current ports design | ✅ exactly | ✗ requires refactor |
| Data loss on switch | None — index was **empty** (0 vectors) | n/a |
| **Chosen** | ✅ **Yes** | Revisit later if desired |

### 4.4 Recreation — first attempt (failed)

Delete succeeded; `create_index` failed:

```
pinecone.errors.exceptions.NotFoundError: [404 NOT_FOUND] Resource cloud: aws region: aped-27b4-a not found
```

`aped-27b4-a` is **not a valid AWS region** — it came from `.env` (`PINECONE_REGION`). It had never mattered before because the original index was created in the console. The subsequent smoke-test `404 not found` was expected fallout (no index existed).

### 4.5 Fix — `.env` region + recreate

```bash
# fix .env
sed -i 's/^PINECONE_REGION=.*/PINECONE_REGION=us-east-1/' .env
sed -i 's/^PINECONE_CLOUD=.*/PINECONE_CLOUD=aws/' .env

# recreate as a PLAIN dense index (no integrated model, no schema)
PYTHONPATH=src .venv/bin/python - <<'PY'
import time
from app.core.config import get_settings
from pinecone import Pinecone, ServerlessSpec

s = get_settings()
pc = Pinecone(api_key=s.pinecone.api_key.get_secret_value())
name = s.pinecone.index_name

pc.create_index(
    name=name,
    dimension=s.pinecone.dimension,          # 1024 — matches cohere/embed-v4.0
    metric="cosine",
    spec=ServerlessSpec(cloud=s.pinecone.cloud, region=s.pinecone.region),
)
while True:
    d = pc.describe_index(name)
    if d.status.ready:
        print(f"READY: {name} dims={d.dimension} metric={d.metric} region={s.pinecone.region}")
        break
    time.sleep(3)
PY
```

> Delete-phase fallback (deletion protection): `pc.configure_index(name, deletion_protection="disabled")` before `pc.delete_index(name)`. Name-release fallback: create under a new name and update `PINECONE_INDEX_NAME`.

### 4.6 Green run

```
$ .venv/bin/python scripts/smoke_vector_and_s3.py
S3 OK: s3://.../smoke/test-1794115843.txt
S3 cleaned up
Vector store stats: {'namespaces': {'__default__': ...vector_count=0}, 'dimension': 1024,
 'metric': 'cosine', 'vector_type': 'dense', 'total_vector_count': 0, ...}
Query hits: [('smoke-0001', 1.0)]
Pinecone cleaned up
```

This is significant: the smoke test exercises **upsert, query, and delete_by_filter** — the exact three operations used by `ingestion.py` and `retrieve.py`. A green smoke test ⇒ ingestion and retrieval will work.

---

## 5. Not a bug: `"Status: no_evidence"` after the fixes

After both fixes, the chat terminal ran cleanly and answered:

```
Answer: I could not find supporting evidence in the available documents.
Status: no_evidence
```

**This is correct behavior.** The index was recreated empty (0 vectors) and the smoke test cleaned up after itself — there is nothing to retrieve. To complete end-to-end validation, ingest a real document:

```bash
PYTHONPATH=src .venv/bin/python - <<'PY'
import uuid
from sqlalchemy import text
from app.application.dependencies.providers import get_db_session, get_storage
from app.application.services.ingestion import process_s3_key

KEY = "smoke/rag-test-doc.txt"
CONTENT = (
    "Project4 internal memo.\n"
    "The secret launch codename is BLUE HERON.\n"
    "The public release is scheduled for Q3 2026.\n"
).encode()

print("uploaded:", get_storage().put(KEY, CONTENT, content_type="text/plain"))

with get_db_session() as session:
    session.execute(
        text("""INSERT INTO documents (id, title, content, source, status)
                VALUES (:id, :title, :content, :source, 'pending')"""),
        {"id": str(uuid.uuid4()), "title": "RAG Smoke Memo",
         "content": CONTENT.decode(), "source": KEY},
    )
print("result:", process_s3_key(KEY))   # expect status='ready', num_chunks=1
PY
```

Then ask: `what is the secret launch codename?` → expect **BLUE HERON** with sources.

**⚠️ Threshold caveat:** `SIMILARITY_THRESHOLD=0.70` is calibrated for OpenAI-style score ranges. **cohere/embed-v4.0 produces much lower absolute cosine scores** (good matches often 0.4–0.6). If logs show `retrieve: N raw hits, 0 above threshold 0.70`, lower it:

```bash
sed -i 's/^SIMILARITY_THRESHOLD=.*/SIMILARITY_THRESHOLD=0.40/' .env
```

Tune upward later until junk results start appearing.

---

## 6. Final verification checklist

| # | Check | Command | Result |
|---|-------|---------|--------|
| 1 | S3 roundtrip | `python scripts/smoke_vector_and_s3.py` | ✅ put/get/presign/delete |
| 2 | Pinecone upsert + query + delete_by_filter | same script | ✅ `Query hits: [('smoke-0001', 1.0)]` |
| 3 | Embedding dimension matches index | `len(embed_query(...)) == 1024` | ✅ |
| 4 | Guardrail ORM mapping | attribute check (`guard` → `guardrail`) | ✅ |
| 5 | Guardrail persistence | repo `.append(...)` smoke | ✅ `guardrail append OK` |
| 6 | Audit trail | `psql` select on `guardrail_logs` | ✅ rows present |
| 7 | Full chat graph | `python scripts/chat_terminal.py` | ✅ clean run, graceful no_evidence on empty index |
| 8 | Ingestion + grounded answer | ingest script + BLUE HERON question | ✅ |

---

## 7. Files changed / not changed

| File | Change |
|------|--------|
| `db/reference_schema.sql` | Removed stray `ALTER TABLE guardrail_logs ADD COLUMN IF NOT EXISTS guard`; fixed `feedback` FK formatting |
| `src/app/domains/infrastructure/database/models.py` | `GuardrailLog.guardrail` → `guard: Mapped[str] = mapped_column("guardrail", String(64))` |
| `.env` | `PINECONE_REGION` → `us-east-1` (was invalid); optionally `SIMILARITY_THRESHOLD` → `0.40` for cohere |
| Pinecone index | Deleted + recreated as plain dense (1024/cosine) — **no code impact** |
| `postgres_guardrail_log.py`, `guard.py`, `interfaces/*`, `vector_store/pinecone.py`, `providers.py`, `ingestion.py` | **No changes needed** — reviewed, confirmed correct |

---

## 8. Lessons learned & follow-ups

**Lessons**
1. **Schema drift hides in three places** — DDL, ORM models, and the code between them. This incident had the *same* rename drift in two of them, and both failed differently (silent empty table vs. loud TypeError).
2. **"Non-fatal" error handling can hide real breakage for weeks.** Guardrail persistence was swallowed as `(non-fatal)` — chat worked, audit trail didn't. Add a regression test that does a real `repo.append()` against the schema; add a metrics counter for swallowed exceptions.
3. **Verify edits mechanically** (`grep` before/after), not by memory — the first "fix" wasn't actually in the file.
4. **Console-created infrastructure is invisible in code.** The document-schema index existed only in Pinecone's console; nothing in the repo hinted at it. Consider a startup/CI check that asserts the index is a plain dense index with the expected dimension.
5. **Error messages tell the truth** — the 400 text ("writes must go through the documents API") settled the diagnosis when `describe_index` couldn't.

**Follow-ups (polish, not bugs)**
- [ ] `chat_terminal.py`: skip empty input (`if not user_input.strip(): continue`) — currently a bare Enter runs the whole graph.
- [ ] `routing.py`: add a `smalltalk` branch so chit-chat ("hi") answers directly instead of falling through to no_evidence.
- [ ] Pin `requirements.txt` (e.g., `pip freeze > requirements.lock.txt`) — a future Pinecone SDK major bump changed internal architecture before; don't get surprised again.
- [ ] Consider a repeatable `scripts/create_vector_index.py` (dimension/metric/region from settings) so index bootstrap is code, not console clicks.
- [ ] Optional future migration to Pinecone documents API / integrated embeddings (Option B) — deliberate refactor: store interface, ingestion, response mapping.
- [ ] Re-tune `SIMILARITY_THRESHOLD` empirically once real documents are ingested.

---

## Appendix A — Diagnostic commands used

```bash
# SDK + index introspection
python -c "import pinecone; print(pinecone.__version__)"          # 10.3.0
PYTHONPATH=src .venv/bin/python - <<'PY'
from app.core.config import get_settings
from app.application.dependencies.providers import get_embeddings
from pinecone import Pinecone
s = get_settings()
pc = Pinecone(api_key=s.pinecone.api_key.get_secret_value())
for name in pc.list_indexes().names():
    d = pc.describe_index(name)
    print(f"index={name} dims={d.dimension} metric={d.metric}")
v = get_embeddings().embed_query("dimension check")
print("embedding dim:", len(v))
PY

# .env pinecone sanity (never paste the API key)
grep -i "PINECONE" .env

# guardrail mapping + persistence
psql "$DATABASE_URL" -c "SELECT stage, guardrail, outcome, thread_id, created_at
                         FROM guardrail_logs ORDER BY created_at DESC LIMIT 5;"
```

## Appendix B — Reference DDL (final state, guardrail_logs)

```sql
CREATE TABLE IF NOT EXISTS guardrail_logs (
    id VARCHAR(36) PRIMARY KEY,
    thread_id VARCHAR(64),
    stage VARCHAR(16) NOT NULL CONSTRAINT ck_guardrail_stage CHECK (stage IN ('input','output')),
    guardrail VARCHAR(64) NOT NULL,
    outcome VARCHAR(16) NOT NULL CONSTRAINT ck_guardrail_outcome CHECK (
        outcome IN ('blocked','flagged','redacted','allowed')),
    reason TEXT,
    snippet TEXT,
    scores JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_guardrail_thread_id ON guardrail_logs (thread_id);
CREATE INDEX IF NOT EXISTS ix_guardrail_outcome_created ON guardrail_logs (outcome, created_at);
-- NOTE: no `guard` column. ORM attribute `guard` maps to column `guardrail`
-- (models.py: guard: Mapped[str] = mapped_column("guardrail", String(64)))
```

*End of report.*
