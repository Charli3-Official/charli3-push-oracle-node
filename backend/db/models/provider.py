"""Provider model module."""

from uuid import UUID
from typing import Optional
from sqlmodel import Field, SQLModel
from .base import BaseUUIDModel


class ProviderBase(SQLModel):
    """Base model for all provider attributes."""

    name: str
    api_url: str
    path: str
    token: Optional[str]
    adapter_type: str
    feed_id: UUID = Field(foreign_key="feed.id")  # Assuming you have a Feeds table


class Provider(BaseUUIDModel, ProviderBase, table=True):
    """Provider model representing a provider entity."""

    pass  # pylint: disable=unnecessary-pass


class ProviderCreate(ProviderBase):
    """Provider create model used when creating a new provider."""

    pass  # pylint: disable=unnecessary-pass


class ProviderUpdate(ProviderBase):
    """Provider update model used when updating an existing provider."""

    pass  # pylint: disable=unnecessary-pass
