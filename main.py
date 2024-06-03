"""Main file for the backend"""

import argparse
import asyncio
import logging

from backend.app_setup import record_factory, setup_feed_updater, setup_logging
from backend.db.database import init_db
from backend.db.service import periodic_cleanup_task
from backend.utils.config_utils import load_config


async def main(config_file):
    """Main function for the backend."""
    # Load configuration and set up logging
    config = load_config(config_file)
    setup_logging(config)
    logging.setLogRecordFactory(record_factory)

    try:
        # Initialize database
        await init_db()
        logging.info("Database initialized successfully.")
    except Exception as e:
        logging.error("Database initialization failed: %s", e)
        return

    cleanup_task = None
    try:
        # Set up and run the feed updater
        updater = await setup_feed_updater(config)
        cleanup_task = asyncio.create_task(periodic_cleanup_task())
        await updater.run()
    except Exception as e:
        logging.error("Feed updater encountered an error: %s", e)
    finally:
        if cleanup_task is not None:
            cleanup_task.cancel()  # Cancel cleanup task when main task stops


if __name__ == "__main__":
    # Loads configuration file
    parser = argparse.ArgumentParser(
        prog="Charli3 Backends for Node Operator",
        description="Charli3 Backends for Node Opetor.",
    )

    parser.add_argument(
        "-c",
        "--configfile",
        help="Specify a file to override default configuration",
        default="config.yml",
    )

    arguments = parser.parse_args()

    asyncio.run(main(config_file=arguments.configfile))
