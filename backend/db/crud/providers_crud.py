"""Providers CRUD operations."""

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from ..models.provider import Provider, ProviderCreate, ProviderUpdate
from .base_crud import BaseCrud


class ProvidersCrud(BaseCrud[Provider, ProviderCreate, ProviderUpdate]):
    """Providers CRUD operations."""

    async def get_provider_by_name_and_feed_id(
        self, name: str, feed_id: str, adapter_type: str, db_session: AsyncSession
    ) -> Optional[Provider]:
        """Get a single provider by name and feed_id."""
        query = select(Provider).where(
            (Provider.name == name)
            & (Provider.feed_id == feed_id)
            & (Provider.adapter_type == adapter_type)
        )
        result = await db_session.execute(query)
        return result.scalar_one_or_none()


providers_crud = ProvidersCrud(Provider)
