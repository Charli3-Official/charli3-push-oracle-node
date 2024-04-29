"""This module contains a NoOpSession class that is used when the database is not configured. """

import logging
import time

logger = logging.getLogger(__name__)
logging.Formatter.converter = time.gmtime


class NoOpSession:
    """A mock class that simulates a database session object when the database is not configured."""

    async def execute(self, *args, **kwargs):
        """A mock method that simulates a database query."""

        logger.warning("Mock database operation 'execute' called on a no-op session.")
        return MockResult()

    async def add(self, instance):
        """A mock method that simulates a database add operation."""

        logger.warning("Mock database operation 'add' called on a no-op session.")

    async def delete(self, instance):
        """A mock method that simulates a database delete operation."""

        logger.warning("Mock database operation 'delete' called on a no-op session.")

    async def commit(self):
        """A mock method that simulates a database commit operation."""

        logger.warning("Mock database operation 'commit' called on a no-op session.")

    async def rollback(self):
        """A mock method that simulates a database rollback operation."""

        logger.warning("Mock database operation 'rollback' called on a no-op session.")

    async def close(self):
        """A mock method that simulates a database close operation."""

        logger.warning("Mock database operation 'close' called on a no-op session.")

    async def refresh(self, instance):
        """A mock method that simulates a database refresh operation."""

        logger.warning("Mock database operation 'refresh' called on a no-op session.")

    # Add other missing methods here


class MockResult:
    """A mock class that simulates a database result object."""

    def scalar_one_or_none(self):
        """A mock method that simulates a database query result."""
        logger.warning(
            "Mock database operation 'scalar_one_or_none' called on a no-op session."
        )
        return None

    # Implement other methods as needed based on your application's usage of the database result objects
