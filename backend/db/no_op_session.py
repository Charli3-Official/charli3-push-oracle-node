"""This module contains a NoOpSession class that is used when the database is not configured. """

import logging
import time

logger = logging.getLogger(__name__)
logging.Formatter.converter = time.gmtime


class NoOpSession:
    """A mock class that simulates a database session object when the database is not configured."""

    def __init__(self):
        self.unique_warning_logger = UniqueWarningLogger()

    async def execute(self, *args, **kwargs):
        """A mock method that simulates a database query."""

        self.unique_warning_logger.log_warning_once(
            "Mock database operation 'execute' called on a no-op session."
        )
        return MockResult()

    async def add(self, instance):
        """A mock method that simulates a database add operation."""

        self.unique_warning_logger.log_warning_once(
            "Mock database operation 'add' called on a no-op session."
        )

    async def delete(self, instance):
        """A mock method that simulates a database delete operation."""

        self.unique_warning_logger.log_warning_once(
            "Mock database operation 'delete' called on a no-op session."
        )

    async def commit(self):
        """A mock method that simulates a database commit operation."""

        self.unique_warning_logger.log_warning_once(
            "Mock database operation 'commit' called on a no-op session."
        )

    async def rollback(self):
        """A mock method that simulates a database rollback operation."""

        self.unique_warning_logger.log_warning_once(
            "Mock database operation 'rollback' called on a no-op session."
        )

    async def close(self):
        """A mock method that simulates a database close operation."""

        self.unique_warning_logger.log_warning_once(
            "Mock database operation 'close' called on a no-op session."
        )

    async def refresh(self, instance):
        """A mock method that simulates a database refresh operation."""

        self.unique_warning_logger.log_warning_once(
            "Mock database operation 'refresh' called on a no-op session."
        )

    # Add other missing methods here


class MockResult:
    """A mock class that simulates a database result object."""

    def scalar_one_or_none(self):
        """A mock method that simulates a database query result."""
        # logger.warning(
        #     "Mock database operation 'scalar_one_or_none' called on a no-op session."
        # )
        return None

    # Implement other methods as needed based on your application's usage of the database result objects


class UniqueWarningLogger:
    """Logs each unique warning only once."""

    def __init__(self):
        self.logged_warnings = set()  # Set to track already logged warnings

    def log_warning_once(self, message):
        """Log a warning message only once."""
        if message not in self.logged_warnings:
            logger.warning(message)
            self.logged_warnings.add(message)
