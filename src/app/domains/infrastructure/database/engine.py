"""Postgres engine — Async version for high concurrency."""

import urllib.parse
from contextlib import asynccontextmanager
from functools import lru_cache
from typing import Any, AsyncIterator

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.core.config import get_settings


def get_url_and_connect_args():
    s = get_settings().database
    url = s.url.get_secret_value()

    # 1. Ensure it's using asyncpg
    if url.startswith("postgresql://") or url.startswith("postgres://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1).replace(
            "postgres://", "postgresql+asyncpg://", 1
        )

    # 2. Parse and clean URL for asyncpg
    parsed = urllib.parse.urlparse(url)
    query = urllib.parse.parse_qs(parsed.query)

    # 3. CRITICAL FIX: Remove psycopg2/libpq-specific parameters that asyncpg doesn't understand.
    UNSUPPORTED_PARAMS = {
        "sslmode",
        "channel_binding",
        "connect_timeout",
        "keepalives",
        "keepalives_idle",
        "keepalives_interval",
        "keepalives_count",
    }
    for param in UNSUPPORTED_PARAMS:
        query.pop(param, None)

    # 4. Determine if we need SSL (usually yes for cloud, no for local dev)
    hostname = parsed.hostname or ""
    use_ssl = "localhost" not in hostname and "127.0.0.1" not in hostname

    connect_args = {"ssl": True} if use_ssl else {}

    # 5. Rebuild URL without the unsupported parameters
    new_query = urllib.parse.urlencode(query, doseq=True)
    clean_url = urllib.parse.urlunparse(parsed._replace(query=new_query))

    return clean_url, connect_args


@lru_cache(maxsize=1)
def get_engine():
    url, connect_args = get_url_and_connect_args()
    s = get_settings().database

    return create_async_engine(
        url,
        pool_size=s.pool_size,
        max_overflow=s.max_overflow,
        pool_pre_ping=True,
        pool_recycle=1800,
        echo=s.echo,
        connect_args=connect_args,
    )


@lru_cache(maxsize=1)
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=get_engine(), expire_on_commit=False, class_=AsyncSession
    )


@asynccontextmanager
async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Async context manager for database sessions with auto-commit/rollback."""
    async with get_session_factory()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def check_database() -> dict[str, Any]:
    engine = get_engine()
    async with engine.connect() as conn:
        version = await conn.execute(text("SELECT version()"))
        version_str = version.scalar_one()
    return {
        "ok": True,
        "server": version_str.split(" on ")[0],
        "tables": sorted((await inspect(engine)).get_table_names()),
    }
