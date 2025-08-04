# db/sessions/database.py

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base

from core.config import settings

# ✅ Correct base class
Base = declarative_base()

# ✅ Global engine and session
_engine = None
_async_session_local = None


def get_async_session_local():
    if _async_session_local is None:
        raise RuntimeError("Database session is not initialized. Call init_db() first.")
    return _async_session_local


async def init_db():
    global _engine, _async_session_local

    
    from db.models.base import Base  # 👈 if you're using a central Base here

    database_url = settings.DATABASE_URL
    print(f"[init_db] Using DATABASE_URL: {database_url}")

    _engine = create_async_engine(
        database_url,
        echo=settings.DEBUG,
        future=True,
    )

    _async_session_local = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # ✅ Correctly create tables using async engine
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    print("✅ All tables created")


async def shutdown_db():
    if _engine:
        await _engine.dispose()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    session_factory = get_async_session_local()
    async with session_factory() as session:
        yield session


# Alias for use in dependencies
get_db_session = get_db
