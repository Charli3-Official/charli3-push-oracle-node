"""Model for the node aggregations entity."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlmodel import Field, SQLModel

from .base import BaseUUIDModel


class NodeAggregationBase(SQLModel):
    """Base model for all node operation attributes."""

    node_pkh: str = Field(foreign_key="node.pub_key_hash")
    feed_id: UUID = Field(foreign_key="feed.id")
    timestamp: datetime
    status: str
    aggregated_value: Optional[Decimal] = Field(default=None, nullable=True)
    nodes_count: Optional[int] = Field(default=None, nullable=True)
    tx_hash: Optional[str] = Field(default=None, nullable=True, index=True)
    trigger: Optional[str] = Field(default=None, nullable=True)


class NodeAggregation(NodeAggregationBase, BaseUUIDModel, table=True):
    """NodeAggregation model representing the node operation entity."""

    pass  # pylint: disable=unnecessary-pass


class NodeAggregationCreate(NodeAggregationBase):
    """Model for creating a new node operation."""

    pass  # pylint: disable=unnecessary-pass


class NodeAggregationUpdate(NodeAggregationBase):
    """Model for updating an existing node operation."""

    pass  # pylint: disable=unnecessary-pass
