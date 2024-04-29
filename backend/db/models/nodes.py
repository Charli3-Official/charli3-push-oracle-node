"""Model for the nodes table."""

from uuid import UUID
from sqlmodel import Field, SQLModel
from .base import BaseUUIDModel


class NodeBase(SQLModel):
    """Base model for all node attributes."""

    feed_id: UUID = Field(foreign_key="feed.id")
    pub_key_hash: str = Field(index=True, unique=True)
    node_operator_address: str


class Node(NodeBase, BaseUUIDModel, table=True):
    """Node model representing the node entity."""

    pass  # pylint: disable=unnecessary-pass


class NodeCreate(NodeBase):
    """Model for creating a new node."""

    pass  # pylint: disable=unnecessary-pass


class NodeUpdate(NodeBase):
    """Model for updating an existing node."""

    pass  # pylint: disable=unnecessary-pass
