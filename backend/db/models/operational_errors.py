""" This module contains the OperationalError model and its related classes."""

from typing import Optional
from sqlmodel import Field, SQLModel
from .base import BaseUUIDModel


class OperationalErrorBase(SQLModel):
    """Base model for all operational error attributes."""

    error_type: str
    error_message: str
    error_context: Optional[str] = Field(default=None, nullable=True)
    error_traceback: Optional[str] = Field(default=None, nullable=True)


class OperationalError(OperationalErrorBase, BaseUUIDModel, table=True):
    """OperationalError model representing the operational error entity."""

    pass  # pylint: disable=unnecessary-pass


class OperationalErrorCreate(OperationalErrorBase):
    """Model for creating a new operational error."""

    pass  # pylint: disable=unnecessary-pass


class OperationalErrorUpdate(OperationalErrorBase):
    """Model for updating an existing operational error."""

    pass  # pylint: disable=unnecessary-pass
