

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

from core.config import settings
from core.secrets_dependencies import fetch_secrets_from_vault
from core.secrets import initialize_secrets, get_secrets_manager
from db.sessions.database import init_db, shutdown_db, get_db

logger = logging.getLogger("core.lifespan")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        logger.info("🚀 Starting up FastAPI application...")

        # 1️⃣ Initialize enhanced secrets management system
        try:
            secrets = await initialize_secrets()
            secrets_manager = get_secrets_manager()
            logger.info(f"🔐 Enhanced secrets system initialized (Vault: {secrets_manager.is_vault_available})")
            
            # Load secrets into settings using the new system
            await settings.load_vault_secrets()
            
        except Exception as e:
            logger.warning(f"⚠️  Enhanced secrets failed, falling back to legacy: {e}")
            # Fallback to legacy secrets fetching
            try:
                legacy_secrets = await fetch_secrets_from_vault()
                settings.POSTGRES_DB = legacy_secrets.get("SOURCE_DB_NAME", settings.POSTGRES_DB)
                settings.POSTGRES_HOST = legacy_secrets.get("DB_HOST", settings.POSTGRES_HOST)
                settings.POSTGRES_PASSWORD = legacy_secrets.get("DB_PASSWORD", settings.POSTGRES_PASSWORD)
                settings.POSTGRES_PORT = int(legacy_secrets.get("DB_PORT", settings.POSTGRES_PORT))
                settings.POSTGRES_USER = legacy_secrets.get("DB_USER", legacy_secrets.get("DATABASE", settings.POSTGRES_USER))
                logger.info("🔐 Legacy Vault secrets fetched successfully")
            except Exception as legacy_e:
                logger.error(f"❌ Both enhanced and legacy secrets failed: {legacy_e}")
                logger.info("⚠️  Continuing with environment variables")

        logger.info(
            f"✅ Database config loaded: "
            f"user={settings.POSTGRES_USER}, host={settings.POSTGRES_HOST}, port={settings.POSTGRES_PORT}, db={settings.POSTGRES_DB}"
        )
        logger.info(f"🔗 Final DATABASE_URL: {settings.DATABASE_URL}")
        

        # 2️⃣ Initialize DB engine and session
        await init_db()
        app.state.db_session = get_db
        logger.info("✅ Database initialized")
        
        # 3️⃣ Initialize email service
        try:
            from utils.email import email_sender
            logger.info("📧 Email service initialized")
        except Exception as email_e:
            logger.warning(f"⚠️  Email service initialization failed: {email_e}")

        yield

    except Exception as e:
        logger.exception(f"❌ Startup failed: {e}")
        raise e
    finally:
        await shutdown_db()
        logger.info("👋 FastAPI application shutdown.")
