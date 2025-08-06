from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from fastapi import FastAPI

from services.init_roles_permissions import init_roles_permissions
from core.logging_config import get_logger
from db.sessions.database import AsyncSessionLocal, init_db, shutdown_db

logger = get_logger(__name__)


# Lifespan event manager
@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[Any, None]:
    """Handle startup and shutdown events for the FastAPI application."""
    logger.info(msg="Starting up FastAPI application...")
    try:
        await init_db()
        logger.info(msg="Database initialized successfully")

        # Initialize roles, permissions, and mappings
        async with AsyncSessionLocal() as session:
            await init_roles_permissions(session)
            logger.info("Default roles and permissions initialized")

    except Exception as e:
        logger.error(msg=f"Startup failed: {str(e)}")
        raise

    yield

    logger.info(msg="Shutting down FastAPI application...")
    try:
        await shutdown_db()
        logger.info(msg="Database shutdown successfully")
    except Exception as e:
        logger.error(msg=f"Shutdown failed: {str(e)}")
        raise
