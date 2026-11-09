"""Postgres (Render) engine — the ONLY file that knows connection details."""

from functools import lru_cache
from typing import Any

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


@lru_cache(maxsize=1)
def get_engine():
    s = get_settings().database
    url = s.url.get_secret_value()

    # Render's external hostname requires TLS; only append if not already set.
    if "sslmode=" not in url:
        url += ("&" if "?" in url else "?") + "sslmode=require"

    return create_engine(
        url,
        pool_size=s.pool_size,
        max_overflow=s.max_overflow,
        pool_pre_ping=True,  # Render suspends idle DBs -> stale conns; this heals them
        pool_recycle=1800,
        echo=s.echo,
    )


@lru_cache(maxsize=1)
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


def check_database() -> dict[str, Any]:
    """Cheap connectivity probe for smoke tests / health endpoints."""
    engine = get_engine()
    with engine.connect() as conn:
        version = conn.execute(text("SELECT version()")).scalar_one()
    return {
        "ok": True,
        "server": version.split(" on ")[0],
        "tables": sorted(inspect(engine).get_table_names()),
    }
