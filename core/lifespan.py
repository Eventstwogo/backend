# # lifespan.py

# from contextlib import asynccontextmanager
# from typing import Any, AsyncGenerator
# import time
# import atexit

# from fastapi import FastAPI

# from core.logging_config import get_logger
# from core.config import settings
# from core.secrets_dependencies import fetch_secrets_from_vault
# from db.sessions.database import init_db, shutdown_db, get_async_session_local
# # from services.init_roles_permissions import init_roles_permissions

# logger = get_logger(__name__)

# async def populate_settings_from_vault(secrets: dict) -> None:
#     """Populate settings with secrets fetched from Vault."""
#     settings.POSTGRES_DB = secrets.get("SOURCE_DB_NAME", settings.POSTGRES_DB)
#     settings.POSTGRES_HOST = secrets.get("DB_HOST", settings.POSTGRES_HOST)
#     settings.POSTGRES_PASSWORD = secrets.get("DB_PASSWORD", settings.POSTGRES_PASSWORD)
#     settings.POSTGRES_PORT = int(secrets.get("DB_PORT", settings.POSTGRES_PORT))
#     settings.POSTGRES_USER = secrets.get("DB_USER", settings.POSTGRES_USER)

#     if not settings.POSTGRES_USER:
#         settings.POSTGRES_USER = secrets.get("DATABASE", settings.POSTGRES_USER)

#     # Optional extras
#     settings.SMTP_PORT = int(secrets.get("SMTP_PORT", settings.SMTP_PORT))
#     settings.SMTP_HOST = secrets.get("SMTP_SERVER", settings.SMTP_HOST)
#     settings.SMTP_USER = secrets.get("SMTP_LOGIN", settings.SMTP_USER)
#     settings.SMTP_PASSWORD = secrets.get("SENDER_PASSWORD", settings.SMTP_PASSWORD)
#     settings.EMAIL_FROM = secrets.get("SENDER_EMAIL", settings.EMAIL_FROM)
#     settings.SPACES_REGION_NAME = secrets.get("SPACES_REGION_NAME", settings.SPACES_REGION_NAME)
#     settings.SPACES_BUCKET_NAME = secrets.get("SPACES_BUCKET_NAME", settings.SPACES_BUCKET_NAME)
#     settings.SPACES_ACCESS_KEY_ID = secrets.get("SPACES_ACCESS_KEY", settings.SPACES_ACCESS_KEY_ID)
#     settings.SPACES_SECRET_ACCESS_KEY = secrets.get("SPACES_SECRET_KEY", settings.SPACES_SECRET_ACCESS_KEY)

#     if not all([settings.POSTGRES_USER, settings.POSTGRES_PASSWORD, settings.POSTGRES_HOST, settings.POSTGRES_DB]):
#         raise ValueError(
#             f"Missing DB credentials after Vault fetch: user={settings.POSTGRES_USER}, "
#             f"host={settings.POSTGRES_HOST}, port={settings.POSTGRES_PORT}, db={settings.POSTGRES_DB}"
#         )

#     logger.info(f"✅ Database config loaded from Vault: user={settings.POSTGRES_USER}, host={settings.POSTGRES_HOST}, port={settings.POSTGRES_PORT}, db={settings.POSTGRES_DB}")

# @asynccontextmanager
# async def lifespan(app: FastAPI) -> AsyncGenerator[Any, None]:
#     """FastAPI startup and shutdown lifecycle."""
#     start_time = time.time()
#     logger.info("🚀 Starting up FastAPI application...")

#     try:
#         secrets = await fetch_secrets_from_vault()
#         logger.info("🔐 Vault secrets fetched successfully")

#         await populate_settings_from_vault(secrets)
#         logger.info(f"🔗 Final DATABASE_URL: {settings.DATABASE_URL}")

#         await init_db()
#         logger.info("✅ Database initialized")

#         # Use session factory after init_db()
#         session_factory = get_async_session_local()
#         # async with session_factory() as session:
#         #     await init_roles_permissions(session)
#         #     logger.info("🔑 Default roles and permissions initialized")

#         duration = time.time() - start_time
#         logger.info(f"✅ FastAPI started in {duration:.2f} seconds")

#     except Exception as e:
#         logger.error(f"❌ Startup failed: {str(e)}")
#         raise

#     yield

#     logger.info("📦 Shutting down FastAPI application...")
#     try:
#         atexit.register(shutdown_db)
#         await shutdown_db()
#         logger.info("✅ Database shutdown complete")
#     except Exception as e:
#         logger.error(f"❌ Shutdown failed: {str(e)}")
#         raise


import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

from core.config import settings
from core.secrets_dependencies import fetch_secrets_from_vault
from db.sessions.database import init_db, shutdown_db, get_db

logger = logging.getLogger("core.lifespan")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        logger.info("🚀 Starting up FastAPI application...")

        # 1️⃣ Fetch secrets from Vault and apply to settings
        secrets = await fetch_secrets_from_vault()

        settings.POSTGRES_DB = secrets.get("SOURCE_DB_NAME", settings.POSTGRES_DB)
        settings.POSTGRES_HOST = secrets.get("DB_HOST", settings.POSTGRES_HOST)
        settings.POSTGRES_PASSWORD = secrets.get("DB_PASSWORD", settings.POSTGRES_PASSWORD)
        settings.POSTGRES_PORT = int(secrets.get("DB_PORT", settings.POSTGRES_PORT))
        settings.POSTGRES_USER = secrets.get("DB_USER", secrets.get("DATABASE", settings.POSTGRES_USER))

        logger.info("🔐 Vault secrets fetched successfully")
        logger.info(
            f"✅ Database config loaded from Vault: "
            f"user={settings.POSTGRES_USER}, host={settings.POSTGRES_HOST}, port={settings.POSTGRES_PORT}, db={settings.POSTGRES_DB}"
        )
        logger.info(f"🔗 Final DATABASE_URL: {settings.DATABASE_URL}")

        # 2️⃣ Initialize DB engine and session
        await init_db()
        app.state.db_session = get_db
        logger.info("✅ Database initialized")

        yield

    except Exception as e:
        logger.exception(f"❌ Startup failed: {e}")
        raise e
    finally:
        await shutdown_db()
        logger.info("👋 FastAPI application shutdown.")
