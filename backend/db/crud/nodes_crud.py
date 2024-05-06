"""Node CRUD Operations"""

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from ..models.nodes import Node, NodeCreate, NodeUpdate
from .base_crud import BaseCrud


class NodeCrud(BaseCrud[Node, NodeCreate, NodeUpdate]):
    """Node CRUD operations."""

    async def get_node_by_pkh(
        self, pkh: str, db_session: AsyncSession
    ) -> Optional[Node]:
        """Get a single node by address."""
        query = select(Node).where(Node.pub_key_hash == pkh)
        result = await db_session.execute(query)
        return result.scalar_one_or_none()

    async def get_node_by_address(
        self, address: str, db_session: AsyncSession
    ) -> Optional[Node]:
        """Get a single node by address."""
        query = select(Node).where(Node.node_operator_address == address)
        result = await db_session.execute(query)
        return result.scalar_one_or_none()


node_crud = NodeCrud(Node)
