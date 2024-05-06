"""Model for rate data flow entity."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlmodel import Field, SQLModel

from .base import BaseUUIDModel


class RateDataFlowBase(SQLModel):
    """Base model for all rate data flow attributes."""

    provider_id: UUID = Field(foreign_key="provider.id")
    feed_id: UUID = Field(foreign_key="feed.id")
    request_timestamp: datetime
    symbol: str
    response_code: int
    response_body: str
    rate: Optional[Decimal] = None
    rate_type: str
    rate_aggregation_id: Optional[UUID] = Field(
        default=None, nullable=True, foreign_key="aggregatedratedetails.id"
    )


class RateDataFlow(BaseUUIDModel, RateDataFlowBase, table=True):
    """RateDataFlow model representing the rate data flow entity."""

    pass  # pylint: disable=unnecessary-pass


class RateDataFlowCreate(RateDataFlowBase):
    """Model for creating a new rate data flow."""

    pass  # pylint: disable=unnecessary-pass


class RateDataFlowUpdate(RateDataFlowBase):
    """Model for updating an existing rate data flow."""

    pass  # pylint: disable=unnecessary-pass
