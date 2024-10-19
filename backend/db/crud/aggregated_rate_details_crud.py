""" Aggregated Rate Details CRUD Operations """

from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.aggregated_rate_detail import (
    AggregatedRateDetails,
    AggregatedRateDetailsCreate,
    AggregatedRateDetailsUpdate,
)
from .base_crud import BaseCrud


class AggregatedRateDetailsCrud(
    BaseCrud[
        AggregatedRateDetails, AggregatedRateDetailsCreate, AggregatedRateDetailsUpdate
    ]
):
    """Aggregated Rate Details CRUD operations."""

    async def get_unlinked_aggregation_ids(
        self,
        linked_aggregation_ids: list[UUID],
        feed_id: UUID,
        db_session: AsyncSession,
    ) -> list[UUID]:
        """
        Fetches IDs of AggregatedRateDetails that are not linked and older than 24 hours.

        Args:
            linked_aggregation_ids (list[int]): IDs that should not be considered for deletion.
            feed_id (UUID): The feed ID to use for the operation.
            db_session (AsyncSession): The database session to use for the operation.

        Returns:
            list[int]: A list of unlinked and old aggregation IDs.
        """
        twenty_four_hours_ago = datetime.now() - timedelta(hours=24)
        statement = select(AggregatedRateDetails.id).where(
            AggregatedRateDetails.feed_id == feed_id,
            AggregatedRateDetails.created_at < twenty_four_hours_ago,
            AggregatedRateDetails.id.not_in(  # pylint: disable=no-member
                linked_aggregation_ids
            ),
        )
        result = await db_session.execute(statement)
        unlinked_ids = result.scalars().all()
        return unlinked_ids

    async def delete_aggregated_rate_details_by_aggregation_id(
        self, unlinked_aggregation_ids: list[UUID], db_session: AsyncSession
    ) -> int:
        """Delete aggregated rate details by aggregation id."""
        if not unlinked_aggregation_ids:
            return 0

        query = delete(AggregatedRateDetails).where(
            AggregatedRateDetails.id.in_(  # pylint: disable=no-member
                unlinked_aggregation_ids
            )
        )
        result = await db_session.execute(query)
        await db_session.commit()
        return result.rowcount


aggregated_rate_details_crud = AggregatedRateDetailsCrud(AggregatedRateDetails)
