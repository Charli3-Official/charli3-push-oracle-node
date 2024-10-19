"""Node Update CRUD Operations"""

from uuid import UUID

from sqlalchemy import not_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from ..models.node_updates import NodeUpdate, NodeUpdateCreate, NodeUpdateUpdate
from .base_crud import BaseCrud


class NodeUpdateCrud(BaseCrud[NodeUpdate, NodeUpdateCreate, NodeUpdateUpdate]):
    """Node Update CRUD operations."""

    async def get_linked_aggregation_ids(
        self, feed_id: UUID, db_session: AsyncSession
    ) -> list[UUID]:
        """
        Fetches rate aggregation IDs that are linked to node updates and are not None.

        Args:
            feed_id (UUID): The feed ID to use for the operation.
            db_session (AsyncSession): The database session to use for the operation.

        Returns:
            list[int]: A list of linked rate aggregation IDs.
        """
        statement = select(NodeUpdate.rate_aggregation_id).where(
            NodeUpdate.feed_id == feed_id, not_(NodeUpdate.rate_aggregation_id is None)
        )
        result = await db_session.execute(statement)
        linked_ids = result.scalars().all()
        return linked_ids


node_update_crud = NodeUpdateCrud(NodeUpdate)
