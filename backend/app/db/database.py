from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

_engine = None
_session_factory = None


class Base(DeclarativeBase):
    pass


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_async_engine(settings.database_url, echo=settings.debug)
    return _engine


def get_session_factory():
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(), class_=AsyncSession, expire_on_commit=False
        )
    return _session_factory


async def get_db() -> AsyncSession:
    async with get_session_factory()() as session:
        try:
            yield session
        finally:
            await session.close()


def sync_schema(sync_conn) -> None:
    """补齐缺失列，兼容已存在但未走迁移的数据库。"""
    inspector = inspect(sync_conn)
    if "events" not in inspector.get_table_names():
        return

    event_columns = {col["name"] for col in inspector.get_columns("events")}
    dialect = sync_conn.dialect.name
    bool_false = "0" if dialect == "sqlite" else "FALSE"

    migrations = [
        ("completed", f"BOOLEAN NOT NULL DEFAULT {bool_false}"),
        ("remind_at", "TIMESTAMP NULL"),
        ("remind_enabled", f"BOOLEAN NOT NULL DEFAULT {bool_false}"),
        ("push_status", "VARCHAR(32) NOT NULL DEFAULT 'pending'"),
        ("pushed_at", "TIMESTAMP WITH TIME ZONE NULL"),
        ("subscribe_template_id", "VARCHAR(128) NULL"),
    ]

    for col_name, col_def in migrations:
        if col_name not in event_columns:
            sync_conn.execute(
                text(f"ALTER TABLE events ADD COLUMN {col_name} {col_def}")
            )
