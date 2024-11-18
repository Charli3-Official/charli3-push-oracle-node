"""Main file for the backend"""

import argparse
import asyncio
import logging

from backend.app_setup import (
    record_factory,
    setup_feed_updater,
    setup_logging,
    setup_node_and_chain_query,
)
from backend.db.database import init_db
from backend.node_checker import NodeChecker
from backend.utils.config_utils import load_config


async def main(config_file):
    """Main function for the backend."""
    # Load configuration and set up logging
    config = load_config(config_file)

    setup_logging(config)
    logging.setLogRecordFactory(record_factory)

    try:
        node_checker = NodeChecker(config)
        await node_checker.run_initial_checks()
    except Exception as e:  # pylint: disable=broad-except
        logging.error("Node checks failed: %s", e)
        return

    try:
        # Initialize database
        await init_db()
        logging.info("Database initialized successfully.")
    except Exception as e:  # pylint: disable=broad-except
        logging.error("Database initialization failed: %s", e)
        return

    try:
        # Set up and run the feed updater
        node, chainquery, feed = await setup_node_and_chain_query(config)
        await node_checker.run_node_operation_checks(node, chainquery)

        updater = await setup_feed_updater(config, chainquery, feed, node)
        await updater.run()
    except Exception as e:  # pylint: disable=broad-except
        logging.error("Feed updater encountered an error: %s", e)


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
