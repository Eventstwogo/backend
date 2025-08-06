# db/sessions/database.py

import logging
from logging import Logger
from typing import AsyncGenerator

from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from core.config import settings

# from db.events import init_db_event_listeners
from db.models import Base

# Configure logging
logging.basicConfig(level=logging.INFO)
logger: Logger = logging.getLogger(__name__)

# Create async engine with optimized pool settings
engine: AsyncEngine = create_async_engine(
    url=str(settings.DATABASE_URL),
    echo=False,  # settings.environment == "development",  # Enable SQL logging in development
    pool_size=(
        5 if settings.ENVIRONMENT == "production" else 3
    ),  # Smaller pool for dev
    max_overflow=10,  # Allow temporary extra connections
    pool_timeout=30,  # Timeout for acquiring a connection
    pool_pre_ping=True,  # Check connection health before use
    pool_recycle=1800,  # Close and reopen connections after 30 minutes
    isolation_level="READ COMMITTED",  # Default isolation level
    future=True,  # Enable asyncio support
)

# Create async session factory
AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Prevent refreshing objects after commit
    autocommit=False,
    autoflush=False,
)


@retry(
    stop=stop_after_attempt(max_attempt_number=3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(exception_types=OperationalError),
    after=lambda retry_state: logger.warning(
        msg=f"Retrying database connection (attempt {retry_state.attempt_number})"
    ),
)
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a database session for dependency injection.

    Yields:
        AsyncSession: A SQLAlchemy async session for database operations.

    Raises:
        OperationalError: If the database connection fails after retries.
        Exception: For other unexpected errors during session operations.

    Example:
        async def endpoint(db: AsyncSession = Depends(get_db)):
            user = await db.execute(select(User).filter_by(user_id="user_1"))
            return user.scalar_one()
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logger.error("Database session error: %s", str(e))
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to extract AsyncSession from get_db_session."""
    async for session in get_db_session():
        yield session


async def init_db() -> None:
    """Initialize the database by creating all tables.

    Raises:
        OperationalError: If the database connection fails.
        Exception: For other errors during table creation.

    Example:
        await init_db()  # Creates tables for User, Chat, Message, etc.
    """
    try:
        async with engine.begin() as conn:
            logger.info("Creating database tables if they do not exist")
            await conn.run_sync(Base.metadata.create_all, checkfirst=True)
    except OperationalError as e:
        logger.error("Failed to connect to database: %s", str(e))
        raise
    except Exception as e:
        logger.error("Error initializing database: %s", str(e))
        raise


async def shutdown_db() -> None:
    """Dispose of the database engine and close all sessions.

    Raises:
        Exception: If engine disposal fails.

    Example:
        await shutdown_db()  # Clean up database connections on app shutdown
    """
    try:
        logger.info("Shutting down database engine")
        await AsyncSessionLocal().close_all()
        await engine.dispose()
    except Exception as e:
        logger.error("Error shutting down database: %s", str(e))
        raise
