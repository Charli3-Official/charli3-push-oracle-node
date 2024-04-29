"""Model for cardano transactions entity."""

from datetime import datetime
from typing import Optional
from uuid import UUID
from sqlmodel import Field, SQLModel
from .base import BaseUUIDModel


class TransactionBase(SQLModel):
    """Base model for all transaction attributes."""

    node_id: UUID = Field(foreign_key="node.id")
    feed_id: UUID = Field(foreign_key="feed.id")
    timestamp: datetime
    status: str
    tx_hash: str = Field(index=True, unique=True)
    tx_fee: Optional[int] = Field(default=None, nullable=True)
    tx_body: Optional[str] = Field(default=None, nullable=True)


class Transaction(TransactionBase, BaseUUIDModel, table=True):
    """Transaction model representing the transaction entity."""

    pass  # pylint: disable=unnecessary-pass


class TransactionCreate(TransactionBase):
    """Model for creating a new transaction."""

    pass  # pylint: disable=unnecessary-pass


class TransactionUpdate(TransactionBase):
    """Model for updating an existing transaction."""

    pass  # pylint: disable=unnecessary-pass
