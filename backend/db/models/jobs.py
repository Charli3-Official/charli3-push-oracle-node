"""Models for the jobs table."""

from datetime import datetime
from decimal import Decimal as decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import JSON
from sqlmodel import Field, SQLModel

from .base import BaseUUIDModel


class JobBase(SQLModel):
    """Base model for all job attributes."""

    feed_id: UUID = Field(foreign_key="feed.id")
    schedule: decimal = Field(default=0)
    last_run_timestamp: Optional[datetime] = None
    last_run_status: Optional[str] = None
    last_error_id: Optional[UUID] = Field(
        default=None, foreign_key="operationalerror.id"
    )
    next_run_timestamp: Optional[datetime] = None
    parameters: Optional[str] = Field(default=None, sa_column=JSON)


class Job(JobBase, BaseUUIDModel, table=True):
    """Job model representing the job entity."""

    pass  # pylint: disable=unnecessary-pass


class JobCreate(JobBase):
    """Model for creating a new job."""

    pass  # pylint: disable=unnecessary-pass


class JobUpdate(JobBase):
    """Model for updating an existing job."""

    pass  # pylint: disable=unnecessary-pass
