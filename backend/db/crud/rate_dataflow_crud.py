"""Rate Dataflow CRUD Operations"""

from typing import List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import delete, select

from ..models.rate_data_flow import RateDataFlow, RateDataFlowCreate, RateDataFlowUpdate
from .base_crud import BaseCrud


class RateDataFlowCrud(BaseCrud[RateDataFlow, RateDataFlowCreate, RateDataFlowUpdate]):
    """Rate Dataflow CRUD operations."""

    async def get_rate_data_flow_by_aggregation_id(
        self, rate_aggregation_id: UUID, db_session: AsyncSession
    ) -> List[RateDataFlow]:
        """Get rate data flow by rate aggregation id."""
        query = select(RateDataFlow).where(
            RateDataFlow.rate_aggregation_id == rate_aggregation_id
        )
        result = await db_session.execute(query)
        return result.scalars().all()

    async def delete_rate_data_flow_by_aggregation_id(
        self, rate_aggregation_id: List[UUID], db_session: AsyncSession
    ) -> int:
        """Delete rate data flow by rate aggregation id."""
        if not rate_aggregation_id:
            return 0

        query = delete(RateDataFlow).where(
            RateDataFlow.rate_aggregation_id.in_(  # pylint: disable=no-member
                rate_aggregation_id
            )
        )
        result = await db_session.execute(query)
        await db_session.commit()
        return result.rowcount


rate_dataflow_crud = RateDataFlowCrud(RateDataFlow)
