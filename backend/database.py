"""Async SQLAlchemy engine, session factory, and DB helpers."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from config import settings

engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def init_db():
    """Create all tables if they don't exist."""
    from models import User  # noqa: F401 — ensure model is registered

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def migrate_db():
    """Add new columns to existing tables (safe for fresh DBs too)."""
    async with engine.begin() as conn:
        for stmt in [
            "ALTER TABLE analysis_history ADD COLUMN project_type VARCHAR(50) DEFAULT 'wokwi'",
            "ALTER TABLE analysis_history ADD COLUMN source_path VARCHAR(1024)",
            "ALTER TABLE analysis_history ADD COLUMN project_name VARCHAR(255)",
        ]:
            try:
                await conn.execute(text(stmt))
            except Exception:
                pass  # Column already exists


async def get_db() -> AsyncSession:
    """FastAPI dependency that yields a DB session."""
    async with async_session() as session:
        yield session
