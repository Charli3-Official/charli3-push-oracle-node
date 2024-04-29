"""Model for node aggregation participation entity."""

from uuid import UUID
from sqlmodel import Field, SQLModel
from .base import BaseUUIDModel


class NodeAggregationParticipationBase(SQLModel):
    """Base model for all node aggregation participation attributes."""

    aggregation_id: UUID = Field(foreign_key="nodeaggregation.id")
    node_pkh: str = Field(foreign_key="node.pub_key_hash")


class NodeAggregationParticipation(
    BaseUUIDModel, NodeAggregationParticipationBase, table=True
):
    """NodeAggregationParticipation model representing the node aggregation participation entity."""

    pass  # pylint: disable=unnecessary-pass


class NodeAggregationParticipationCreate(NodeAggregationParticipationBase):
    """Model for creating a new node aggregation participation."""

    pass  # pylint: disable=unnecessary-pass


class NodeAggregationParticipationUpdate(NodeAggregationParticipationBase):
    """Model for updating an existing node aggregation participation."""

    pass  # pylint: disable=unnecessary-pass
