import asyncio
import urllib.parse
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context

from app.core.config import get_settings
from app.domains.infrastructure.database.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url_and_connect_args():
    settings = get_settings()
    url = settings.database.url.get_secret_value()

    # 1. Ensure it's using asyncpg
    if url.startswith("postgresql://") or url.startswith("postgres://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1).replace(
            "postgres://", "postgresql+asyncpg://", 1
        )

    # 2. Parse and clean URL for asyncpg
    parsed = urllib.parse.urlparse(url)
    query = urllib.parse.parse_qs(parsed.query)

    # Remove psycopg2-specific 'sslmode' which crashes asyncpg
    query.pop("sslmode", None)

    # Determine if we need SSL (usually yes for cloud, no for local dev)
    hostname = parsed.hostname or ""
    use_ssl = "localhost" not in hostname and "127.0.0.1" not in hostname

    connect_args = {"ssl": True} if use_ssl else {}

    # Rebuild URL without sslmode
    new_query = urllib.parse.urlencode(query, doseq=True)
    clean_url = urllib.parse.urlunparse(parsed._replace(query=new_query))

    return clean_url, connect_args


def run_migrations_offline() -> None:
    url, _ = get_url_and_connect_args()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    url, connect_args = get_url_and_connect_args()

    engine = create_async_engine(
        url,
        poolclass=pool.NullPool,
        connect_args=connect_args,
    )

    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
