"""Print the actual columns of GuardrailLog + ChatMessage so we can see
what attribute names your models.py really defines."""

import sys, os

# bootstrap src/ on path (matches your layout)
HERE = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(HERE)
for c in (PARENT, os.path.join(PARENT, "src")):
    if os.path.isdir(os.path.join(c, "app")):
        sys.path.insert(0, c)
        break

from app.domains.infrastructure.database.models import GuardrailLog, ChatMessage

print("=== GuardrailLog columns ===")
for col in GuardrailLog.__table__.columns:
    print(f"  python attr: {col.key:<20}  db column: {col.name:<20}  type: {col.type}")

print("\n=== GuardrailLog valid constructor kwargs ===")
# SQLAlchemy stores the set of kwargs the declarative constructor accepts
from sqlalchemy import inspect

mapper = inspect(GuardrailLog)
print("  ", sorted(mapper.column_attrs.keys()))

print("\n=== ChatMessage columns (for the meta/metadata pattern) ===")
for col in ChatMessage.__table__.columns:
    print(f"  python attr: {col.key:<20}  db column: {col.name:<20}  type: {col.type}")
