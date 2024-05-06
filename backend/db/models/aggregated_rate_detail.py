# db/models/aggregated_rate_details.py
"""This module contains the AggregatedRateDetails model representing the aggregated rate details entity."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlmodel import Field, SQLModel

from .base import BaseUUIDModel


class AggregatedRateDetailsBase(SQLModel):
    """Base model for all aggregated rate details attributes."""

    feed_id: UUID = Field(foreign_key="feed.id")
    requested_at: datetime
    aggregation_timestamp: datetime
    aggregated_rate: Optional[Decimal] = Field(default=None, nullable=True)
    method: Optional[str] = Field(default=None, nullable=True)


class AggregatedRateDetails(BaseUUIDModel, AggregatedRateDetailsBase, table=True):
    """AggregatedRateDetails model representing the aggregated rate details entity."""

    pass


class AggregatedRateDetailsCreate(AggregatedRateDetailsBase):
    """Model for creating a new aggregated rate details."""

    pass


class AggregatedRateDetailsUpdate(AggregatedRateDetailsBase):
    """Model for updating an existing aggregated rate details."""

    pass
