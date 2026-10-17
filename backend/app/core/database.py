"""SQLAlchemy Async Engine, SessionMaker, Base declarative model, and database dependency."""

from __future__ import annotations

import logging
from typing import AsyncGenerator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

logger = logging.getLogger(__name__)

# Configure engine arguments based on driver
engine_kwargs = {
    "echo": False,
    "future": True,
}

if settings.ASYNC_DATABASE_URL and settings.ASYNC_DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # PostgreSQL pool options
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20

# Create async engine
engine = create_async_engine(
    settings.ASYNC_DATABASE_URL,
    **engine_kwargs,
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


def _switch_to_sqlite() -> None:
    """Seamlessly switch engine and sessionmaker to local SQLite if PostgreSQL is inaccessible."""
    global engine, AsyncSessionLocal
    sqlite_url = "sqlite+aiosqlite:///./narrativelens.db"
    logger.warning(
        f"Primary database connection failed. Falling back to local SQLite ({sqlite_url}) "
        "to ensure full persistence and functionality in standalone development."
    )
    engine = create_async_engine(
        sqlite_url,
        echo=False,
        future=True,
        connect_args={"check_same_thread": False},
    )
    AsyncSessionLocal = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that yields an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_db_connection() -> bool:
    """Check whether database connection is active and responsive, with automatic SQLite fallback."""
    global engine
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.warning(f"Database connection check failed on primary URL: {exc}")
        if "sqlite" not in str(engine.url):
            try:
                _switch_to_sqlite()
                async with engine.begin() as conn:
                    await conn.run_sync(Base.metadata.create_all)
                async with engine.connect() as conn:
                    await conn.execute(text("SELECT 1"))
                logger.info("Successfully connected to and verified local SQLite database.")
                return True
            except Exception as sql_exc:
                logger.error(f"Fallback SQLite connection failed: {sql_exc}")
        return False


async def init_db() -> None:
    """Create all tables in the database (primarily used in dev / testing environments)."""
    global engine
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as exc:
        logger.warning(f"Primary database init failed ({exc}); switching to SQLite fallback...")
        if "sqlite" not in str(engine.url):
            _switch_to_sqlite()
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Local SQLite database schemas initialized successfully.")
        else:
            raise
