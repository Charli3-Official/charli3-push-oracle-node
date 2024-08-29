""" This script is used to run database migrations."""

import logging

from alembic import command
from alembic.config import Config
from backend.db.database import get_database_url

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migrations():
    """Run database migrations using Alembic."""
    db_url = get_database_url()

    if not db_url:
        logger.error(
            "Database URL not found in configuration. Migrations cannot be run."
        )
        return

    logger.info("Running database migrations...")
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)

    try:
        command.upgrade(alembic_cfg, "head")
        logger.info("Database migrations completed successfully.")
    except Exception as e:
        logger.error("Error occurred during migrations: %s", str(e))
        raise


if __name__ == "__main__":
    run_migrations()
