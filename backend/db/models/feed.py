""" SQL model for feed"""

from sqlmodel import SQLModel
from .base import BaseUUIDModel


class FeedBase(SQLModel):
    """Base model for feed."""

    title: str
    feed_address: str
    aggstate_nft: str
    oracle_nft: str
    node_nft: str
    reward_nft: str
    oracle_currency: str


class Feed(FeedBase, BaseUUIDModel, table=True):
    """Model for feed."""

    pass  # pylint: disable=unnecessary-pass


class FeedCreate(FeedBase):
    """Model for creating a feed."""

    pass  # pylint: disable=unnecessary-pass


class FeedUpdate(FeedBase):
    """Model for updating a feed."""

    pass  # pylint: disable=unnecessary-pass
