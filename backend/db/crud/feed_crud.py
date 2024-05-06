"""Feed CRUD operations."""

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from ..models.feed import Feed, FeedCreate, FeedUpdate
from .base_crud import BaseCrud


class FeedCrud(BaseCrud[Feed, FeedCreate, FeedUpdate]):
    """Feed CRUD operations."""

    async def get_feed_by_address(
        self, address: str, db_session: AsyncSession
    ) -> Optional[Feed]:
        """Get a single feed by address."""
        query = select(Feed).where(Feed.feed_address == address)
        result = await db_session.execute(query)
        return result.scalar_one_or_none()


feed_crud = FeedCrud(Feed)
