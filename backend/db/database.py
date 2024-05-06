"""Database connection and session management."""

import logging
import time
from contextlib import asynccontextmanager

import yaml
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

from backend.db.no_op_session import NoOpSession

# Initialize logging
logger = logging.getLogger("database")
logging.Formatter.converter = time.gmtime

# Initialize DATABASE_URL to None
DATABASE_URL = None

# Try to load configuration from the config.yml file
try:
    with open("config.yml", encoding="utf-8") as ymlfile:
        config = yaml.load(ymlfile, Loader=yaml.FullLoader)
        # Safely get the database URL if it exists
        DATABASE_URL = config.get("database", {}).get("url", None)
except FileNotFoundError:
    logger.error(
        "Configuration file not found. Proceeding without a database connection..."
    )


# Function to check if the database is configured
def is_database_configured():
    """Check if the database is configured by checking if DATABASE_URL is set."""
    return DATABASE_URL is not None


# Conditional engine creation based on DATABASE_URL presence
if is_database_configured():
    engine = create_async_engine(DATABASE_URL)
else:
    # Notify about missing DATABASE_URL or proceed with no database setup
    logger.error(
        "Database URL not provided. The application will run without database functionality."
    )
    engine = None

# Conditional sessionmaker configuration
if engine:
    AsyncSessionLocal = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
else:
    AsyncSessionLocal = None


async def init_db() -> None:
    """Initialize the database by creating all defined tables. This is an asynchronous operation."""
    if not engine:
        logger.info("No database configured. Skipping database initialization.")
        return

    async with engine.begin() as conn:
        # Use SQLModel's metadata to create all tables
        await conn.run_sync(SQLModel.metadata.create_all)


@asynccontextmanager
async def get_session():
    """Dependency that provides a SQLAlchemy AsyncSession
    that is automatically closed after the request."""

    if not AsyncSessionLocal:
        logger.warning(
            "Database operations are not available. Skipping session creation."
        )
        yield NoOpSession()
        return

    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error("An error occurred during session management: %s", e)
            raise
        finally:
            await session.close()


async def close_db() -> None:
    """
    Close the database connection.
    This function should be called when the application shuts down.
    """
    if engine is None:
        logger.info("Database engine is not initialized. No need to close connections.")
        return
    await engine.dispose()
