"""Model for the node updates entity."""

from datetime import datetime
from typing import Optional
from uuid import UUID
from sqlmodel import Field, SQLModel
from .base import BaseUUIDModel


class NodeUpdateBase(SQLModel):
    """Base model for all node update attributes."""

    node_id: UUID = Field(foreign_key="node.id")
    feed_id: UUID = Field(foreign_key="feed.id")
    timestamp: datetime
    status: str
    updated_value: Optional[int] = Field(default=None, nullable=True)
    rate_aggregation_id: Optional[UUID] = Field(
        default=None, foreign_key="aggregatedratedetails.id", nullable=True
    )
    tx_hash: Optional[str] = Field(
        default=None, foreign_key="transaction.tx_hash", nullable=True, index=True
    )
    trigger: Optional[str] = Field(default=None, nullable=True)


class NodeUpdate(NodeUpdateBase, BaseUUIDModel, table=True):
    """NodeUpdate model representing the node update entity."""

    pass  # pylint: disable=unnecessary-pass


class NodeUpdateCreate(NodeUpdateBase):
    """Model for creating a new node update."""

    pass  # pylint: disable=unnecessary-pass


class NodeUpdateUpdate(NodeUpdateBase):
    """Model for updating an existing node update."""

    pass  # pylint: disable=unnecessary-pass
