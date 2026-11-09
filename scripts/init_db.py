"""Create the schema from the SQLAlchemy models, then verify it end-to-end.

Run from Project4/:
    PYTHONPATH=src python scripts/init_db.py

Safe to re-run: create_all only ADDS missing tables, and the probe rows are
rolled back, so nothing is ever left behind.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.domains.infrastructure.database.engine import check_database, get_engine
from app.domains.infrastructure.database.models import (
    Approval,
    AuditEvent,
    Base,
    ChatMessage,
    Document,
    Feedback,
    GuardrailLog,
)

EXPECTED = {
    "documents",
    "chat_history",
    "approvals",
    "feedback",
    "audit_events",
    "guardrail_logs",
}


def create_schema() -> list[str]:
    engine = get_engine()
    Base.metadata.create_all(engine)
    return sorted(inspect(engine).get_table_names())


def verify_roundtrip() -> None:
    """Insert one probe row per table, read it back, then ROLL BACK."""
    probes = [
        Document(title="__probe__", content="__probe__", status="ready"),
        ChatMessage(thread_id="__probe__", role="user", content="__probe__"),
        Approval(
            thread_id="__probe__", request_type="__probe__", payload={"probe": True}
        ),
        Feedback(thread_id="__probe__", rating=5),
        AuditEvent(action="probe.run", actor_type="system"),
        GuardrailLog(stage="input", guardrail="__probe__", outcome="blocked"),
    ]

    session = Session(get_engine())
    try:
        session.add_all(probes)
        session.flush()  # assigns PKs + fires CHECK constraints now

        assert session.query(Document).filter_by(title="__probe__").one()
        assert session.query(ChatMessage).filter_by(thread_id="__probe__").one()
        assert session.query(Approval).filter_by(thread_id="__probe__").one()
        assert session.query(Feedback).filter_by(thread_id="__probe__").one()
        assert session.query(AuditEvent).filter_by(action="probe.run").one()
        assert session.query(GuardrailLog).filter_by(guardrail="__probe__").one()
        print("  insert + read-back probes: OK")
    finally:
        session.rollback()  # probe rows are never persisted
        session.close()


def main() -> None:
    # print host/db only — never credentials
    print(f"Target: {get_settings().database.url.get_secret_value().split('@')[-1]}")

    info = check_database()
    print(f"Connected: {info['server']}")

    tables = create_schema()
    print(f"Tables ({len(tables)}): {', '.join(tables)}")

    if missing := EXPECTED - set(tables):
        sys.exit(f"MISSING tables: {sorted(missing)}")
    print("All 6 expected tables present.")

    verify_roundtrip()
    print("\nSchema created and verified ✔")


if __name__ == "__main__":
    main()
