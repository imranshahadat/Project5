# Project4 — Database Architecture

> **Scope:** persistence layer only — schema, connection management, repositories,
> and schema setup/verification. Providers, LLMs and embeddings are covered in
> `ARCHITECTURE.md`.

## 1. Overview

| Aspect         | Choice                                                        |
|----------------|---------------------------------------------------------------|
| Database       | PostgreSQL 16, hosted on **Render**                           |
| ORM            | SQLAlchemy 2.0 (`DeclarativeBase`, `Mapped`, `mapped_column`) |
| Config         | pydantic-settings — `DatabaseSettings`, driven by `.env`      |
| TLS            | `sslmode=require` auto-appended in `engine.py`                |
| Setup/verify   | `scripts/init_db.py` (idempotent)                             |
| Reference DDL  | `db/reference_schema.sql` (kept in sync, docs / psql bootstrap) |

One table per concern:

| Concern          | Table           | Written by            |
|------------------|-----------------|-----------------------|
| Document storage | `documents`     | ingestion pipeline    |
| Chat memory      | `chat_history`  | agent loop            |
| HITL approvals   | `approvals`     | agent + human reviewer|
| User feedback    | `feedback`      | UI                    |
| Audit trail      | `audit_events`  | cross-cutting logger  |
| Guardrail events | `guardrail_logs`| input/output guardrails|

## 2. Entity relationships

```text
                ┌───────────────┐
                │   documents   │   ingested content + metadata
                └───────────────┘

┌───────────────────┐    same thread_id     ┌───────────────┐
│   chat_history    │◄─────────────────────►│   approvals   │
│  (agent memory)   │     (logical, no FK)  │  (HITL gate)  │
└─────────┬─────────┘                       └───────────────┘
          │
          │ FK: feedback.message_id → chat_history.id (ON DELETE SET NULL)
          ▼
┌───────────────────┐
│     feedback      │
└───────────────────┘

┌───────────────────┐        ┌──────────────────┐
│   audit_events    │        │  guardrail_logs  │   append-only, no FKs
└───────────────────┘        └──────────────────┘
```

There is exactly **one real foreign key** in the whole schema. `thread_id`
correlates rows across `chat_history` / `approvals` / `feedback` *logically*,
and the two log tables are intentionally standalone — logs must never fail to
insert (or be cascade-deleted) because of referential rules.

## 3. Table reference

### 3.1 `documents`

| Column       | Type         | Constraints / Default        | Notes                        |
|--------------|--------------|------------------------------|------------------------------|
| `id`         | VARCHAR(36)  | PK, default `uuid4()`        | string UUID — portable       |
| `title`      | VARCHAR(512) | NOT NULL                     |                              |
| `content`    | TEXT         | NOT NULL                     | raw text body                |
| `source`     | VARCHAR(512) | nullable                     | URL / file path              |
| `status`     | VARCHAR(20)  | NOT NULL DEFAULT `'pending'` | CHECK: pending/processing/ready/failed |
| `created_at` | TIMESTAMPTZ  | NOT NULL DEFAULT `now()`     | server-side                  |
| `updated_at` | TIMESTAMPTZ  | NOT NULL DEFAULT `now()`     | ORM `onupdate`               |

Index `(status, created_at)` serves the ingestion-queue query
("oldest pending documents first").

### 3.2 `chat_history`

| Column       | Type        | Constraints / Default    | Notes                                    |
|--------------|-------------|--------------------------|------------------------------------------|
| `id`         | VARCHAR(36) | PK                       |                                          |
| `thread_id`  | VARCHAR(64) | NOT NULL                 | one conversation = one thread            |
| `role`       | VARCHAR(16) | NOT NULL                 | CHECK: system/user/assistant/tool        |
| `content`    | TEXT        | NOT NULL                 |                                          |
| `doc_ids`    | JSONB       | nullable                 | retrieved document ids — RAG traceability|
| `metadata`   | JSONB       | nullable                 | model, token counts, latency (ORM attr `meta`) |
| `created_at` | TIMESTAMPTZ | NOT NULL DEFAULT `now()` |                                          |

Index `(thread_id, created_at)` serves timeline reads
("last N turns of this conversation, oldest first").

### 3.3 `approvals` (HITL)

| Column          | Type         | Constraints / Default        | Notes                          |
|-----------------|--------------|------------------------------|--------------------------------|
| `id`            | VARCHAR(36)  | PK                           |                                |
| `thread_id`     | VARCHAR(64)  | NOT NULL                     |                                |
| `request_type`  | VARCHAR(64)  | NOT NULL                     | e.g. `send_email`, `run_tool`  |
| `payload`       | JSONB        | NOT NULL                     | exactly what the agent wants to do |
| `status`        | VARCHAR(16)  | DEFAULT `'pending'`          | CHECK: pending/approved/rejected/expired |
| `requested_by`  | VARCHAR(128) | nullable                     |                                |
| `decided_by`    | VARCHAR(128) | nullable                     |                                |
| `decision_note` | TEXT         | nullable                     | reviewer's comment             |
| `requested_at`  | TIMESTAMPTZ  | NOT NULL DEFAULT `now()`     |                                |
| `decided_at`    | TIMESTAMPTZ  | nullable                     |                                |
| `expires_at`    | TIMESTAMPTZ  | nullable                     | timeout → marked `expired`     |

Indexes: `thread_id`; `(status, requested_at)` serves the reviewer's pending
queue and any background expiry sweep.

### 3.4 `feedback`

| Column       | Type        | Constraints / Default    | Notes                                  |
|--------------|-------------|--------------------------|----------------------------------------|
| `id`         | VARCHAR(36) | PK                       |                                        |
| `thread_id`  | VARCHAR(64) | NOT NULL                 |                                        |
| `message_id` | VARCHAR(36) | nullable **FK**          | → `chat_history.id` ON DELETE SET NULL |
| `rating`     | SMALLINT    | nullable                 | CHECK: 1–5 or NULL                     |
| `is_helpful` | BOOLEAN     | nullable                 | thumbs up / down                       |
| `category`   | VARCHAR(64) | nullable                 | e.g. `accuracy`                        |
| `comment`    | TEXT        | nullable                 |                                        |
| `created_at` | TIMESTAMPTZ | NOT NULL DEFAULT `now()` |                                        |

### 3.5 `audit_events`

| Column        | Type         | Constraints / Default    | Notes                              |
|---------------|--------------|--------------------------|------------------------------------|
| `id`          | VARCHAR(36)  | PK                       |                                    |
| `actor`       | VARCHAR(128) | DEFAULT `'system'`       | user id / agent name               |
| `actor_type`  | VARCHAR(16)  | DEFAULT `'system'`       | CHECK: user/agent/system           |
| `action`      | VARCHAR(128) | NOT NULL                 | dotted verb, e.g. `approval.granted` |
| `entity_type` | VARCHAR(64)  | nullable                 | `document`, `approval`, …          |
| `entity_id`   | VARCHAR(36)  | nullable                 |                                    |
| `detail`      | JSONB        | nullable                 | structured context                 |
| `ip_address`  | VARCHAR(45)  | nullable                 | IPv6-safe                          |
| `created_at`  | TIMESTAMPTZ  | NOT NULL DEFAULT `now()` |                                    |

Indexes: `(action, created_at)` for "what happened recently of type X";
`(entity_type, entity_id)` for an entity's full history.

### 3.6 `guardrail_logs`

| Column       | Type        | Constraints / Default    | Notes                                    |
|--------------|-------------|--------------------------|------------------------------------------|
| `id`         | VARCHAR(36) | PK                       |                                          |
| `thread_id`  | VARCHAR(64) | nullable                 |                                          |
| `stage`      | VARCHAR(16) | NOT NULL                 | CHECK: input/output                      |
| `guardrail`  | VARCHAR(64) | NOT NULL                 | e.g. `pii_filter`, `prompt_injection`    |
| `outcome`    | VARCHAR(16) | NOT NULL                 | CHECK: blocked/flagged/redacted/allowed  |
| `reason`     | TEXT        | nullable                 |                                          |
| `snippet`    | TEXT        | nullable                 | **truncated** — may contain PII          |
| `scores`     | JSONB       | nullable                 | confidence, thresholds                   |
| `created_at` | TIMESTAMPTZ | NOT NULL DEFAULT `now()` |                                          |

Indexes: `thread_id`; `(outcome, created_at)` for "blocked events, last 24h".

## 4. Design conventions

- **String UUIDs** (`VARCHAR(36)`) everywhere — portable, debuggable, matches the
  original `Document` model.
- **CHECK constraints instead of PG enums** — adding a status later is a
  one-line migration instead of an enum-alter dance.
- **`TIMESTAMPTZ` for all timestamps** — no naive datetimes, ever.
- **JSONB for semi-structured data** (`payload`, `detail`, `metadata`, `scores`,
  `doc_ids`) — schema-free extras without new tables.
- **No FKs on append-only tables** (`audit_events`, `guardrail_logs`) — logging
  must never fail or cascade.
- **One real FK**: `feedback.message_id → chat_history.id ON DELETE SET NULL` —
  feedback survives message deletion.
- The ORM attribute is `meta` mapped to column `metadata` because `.metadata`
  is reserved by SQLAlchemy's declarative API.

## 5. Connection & session management

`src/app/domains/infrastructure/database/engine.py` is the **only** file that
knows connection details:

```python
@lru_cache(maxsize=1)
def get_engine():
    s = get_settings().database
    url = s.url.get_secret_value()

    # Render's external hostname requires TLS; only append if not already set.
    if "sslmode=" not in url:
        url += ("&" if "?" in url else "?") + "sslmode=require"

    return create_engine(
        url,
        pool_size=s.pool_size,        # 5
        max_overflow=s.max_overflow,  # 5  -> hard ceiling of 10 connections
        pool_pre_ping=True,           # Render suspends idle DBs -> heals stale conns
        pool_recycle=1800,            # recycle conns older than 30 min
        echo=s.echo,
    )
```

Transactions follow one pattern — the composition root owns commit/rollback:

```python
@contextmanager
def get_db_session() -> Iterator[Session]:
    """One transaction per `with` block: commit on success, rollback on error."""
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

Also exposed: `check_database()` — a `SELECT version()` + table-list probe used
by the setup script and (later) health endpoints.

## 6. Repository layer (ports & adapters)

| Port (`domains/interfaces/`)        | Adapter (`infrastructure/database/`)     | Purpose                    |
|-------------------------------------|------------------------------------------|----------------------------|
| `BaseDocumentRepository`            | `PostgresDocumentRepository`             | add / get / list documents |
| `BaseChatRepository`                | `PostgresChatRepository`                 | append / history / clear   |

Domain code never imports SQLAlchemy — only the ports.

```python
from app.application.dependencies.providers import get_chat_repository

with get_chat_repository() as chat:
    chat.append("thread-123", "user", "Summarise the architecture doc")
    chat.append("thread-123", "assistant", "It's a hexagonal architecture ...")
    for m in chat.history("thread-123"):
        print(m["role"], "->", m["content"][:60])
```

## 7. Schema creation & verification

`scripts/init_db.py` performs, in order:

1. Load settings — fail fast with `ConfigError` if `DATABASE_URL` is missing.
2. `check_database()` — connectivity probe, prints server version.
3. `Base.metadata.create_all()` — **idempotent**: creates only missing tables.
4. Assert the six expected tables exist; exit non-zero otherwise.
5. **Probe round-trip** — insert one row into every table, `flush()` (fires all
   CHECK constraints), read each back, then `rollback()`. Verifies the schema
   end-to-end while leaving zero rows behind.

Expected output:

```text
Target: dpg-xxxx.oregon-postgres.render.com/project4_db
Connected: PostgreSQL 16.x
Tables (6): approvals, audit_events, chat_history, documents, feedback, guardrail_logs
All 6 expected tables present.
  insert + read-back probes: OK

Schema created and verified ✔
```

Manual alternative: `psql "$DATABASE_URL" -f db/reference_schema.sql`, then
`psql "$DATABASE_URL" -c '\dt'`.

## 8. Operations notes (Render)

- Use the **External Database URL** for local development; the Internal URL only
  resolves from services running on Render.
- `sslmode=require` is appended automatically if missing.
- `pool_pre_ping` + `pool_recycle=1800` absorb Render's idle-suspension behaviour
  (same trick the config used for Neon).
- Connection budget: `pool_size 5 + max_overflow 5 = 10` — do not raise it much;
  lower Render tiers have tight connection limits.
- Render's **free Postgres expires after ~30 days** — fine for demos, not for
  durable storage.

## 9. File map

```text
Project4/
├── db/
│   └── reference_schema.sql                  # raw DDL mirror (docs / psql bootstrap)
├── scripts/
│   └── init_db.py                            # create_all + probe verification
└── src/app/
    ├── application/dependencies/providers.py # get_db_session, get_chat_repository
    ├── core/config.py                        # DatabaseSettings (url, pool, echo)
    └── domains/
        ├── interfaces/
        │   ├── repositories.py               # port: BaseDocumentRepository
        │   └── chat.py                       # port: BaseChatRepository
        └── infrastructure/database/
            ├── engine.py                     # engine, sessionmaker, health probe
            ├── models.py                     # 6 tables — source of truth
            └── postgres_repositories.py      # adapters (document, chat)
```

## 10. Roadmap

- `BaseApprovalRepository` port + adapter (create → poll → decide → expire).
- `AuditLogger` helper writing `audit_events` / `guardrail_logs` around the
  agent loop.
- Pinecone vector store (separate infrastructure — deliberately **not** in this
  database).
- Introduce Alembic migrations once the schema stabilises.
