"""Database service functions."""

import asyncio
import logging
import time
import traceback
from datetime import datetime
from typing import Any, Dict, List
from uuid import UUID

from charli3_offchain_core import NodeDatum, RewardDatum
from pycardano import Address, Network, UTxO, VerificationKeyHash
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import get_session

from .crud.aggregated_rate_details_crud import aggregated_rate_details_crud
from .crud.jobs_crud import jobs_crud
from .crud.node_aggregation_participation_crud import (
    node_aggregation_participation_crud,
)
from .crud.node_updates_crud import node_update_crud
from .crud.nodes_crud import node_crud
from .crud.operational_errors_crud import operational_errors_crud
from .crud.rate_dataflow_crud import rate_dataflow_crud
from .crud.reward_distribution_crud import reward_distribution_crud
from .models import (
    AggregatedRateDetails,
    AggregatedRateDetailsCreate,
    Job,
    JobCreate,
    Node,
    NodeAggregationParticipationCreate,
    NodeCreate,
    OperationalErrorCreate,
    RateDataFlowCreate,
    RewardDistributionCreate,
)

# Initialize logging
logger = logging.getLogger("database")
logging.Formatter.converter = time.gmtime


def get_traceback_str(exception):
    """Get a formatted traceback string from an exception."""
    return "".join(
        traceback.format_exception(
            type(exception), value=exception, tb=exception.__traceback__
        )
    )


async def get_or_create_node(db_session: AsyncSession, node: NodeCreate) -> Node:
    """Ensure a node exists, or create it."""
    existing_node = await node_crud.get_node_by_pkh(node.pub_key_hash, db_session)
    if existing_node:
        return existing_node
    return await node_crud.create(db_session=db_session, obj_in=node)


async def process_and_store_nodes_data(
    nodes_datum: List[NodeDatum],
    network: Network,
    feed_id: str,
    db_session: AsyncSession,
):
    """Get a list of nodes from a list of NodeDatum."""
    for node in nodes_datum:
        pub_key_hash = VerificationKeyHash(node.node_state.ns_operator)
        address = str(Address(pub_key_hash, network=network))
        node_create = NodeCreate(
            feed_id=feed_id,
            pub_key_hash=str(pub_key_hash),
            node_operator_address=address,
        )
        await get_or_create_node(db_session, node_create)


async def store_aggregated_rate_details(
    db_session: AsyncSession, aggregated_rate: int, feed_id: str, requested_at
) -> AggregatedRateDetails:
    """Store aggregated rate details."""
    aggregated_rate_details = AggregatedRateDetailsCreate(
        feed_id=feed_id,
        requested_at=requested_at,
        aggregation_timestamp=datetime.now(),
        aggregated_rate=aggregated_rate,
        method="median",
    )
    return await aggregated_rate_details_crud.create(
        db_session=db_session, obj_in=aggregated_rate_details
    )


async def store_rate_dataflow(
    db_session: AsyncSession, all_provider_responses: List[Dict[str, Any]]
) -> None:
    """Store all provider responses."""
    for provider_response in all_provider_responses:
        rate_dataflow = RateDataFlowCreate(
            provider_id=provider_response["provider_id"],
            feed_id=provider_response["feed_id"],
            request_timestamp=provider_response["request_timestamp"],
            symbol=provider_response["symbol"],
            response_code=provider_response["response_code"],
            response_body=provider_response["response_body"],
            rate=provider_response["rate"],
            rate_aggregation_id=provider_response["rate_aggregation_id"],
            rate_type=provider_response["rate_type"],
        )
        await rate_dataflow_crud.create(db_session=db_session, obj_in=rate_dataflow)


async def store_node_aggregation_participation(
    db_session: AsyncSession, aggregation_id: str, node_utxos: List[UTxO]
) -> None:
    """Store node aggregation participation."""
    for utxo in node_utxos:
        node_datum: NodeDatum = utxo.output.datum
        if not isinstance(node_datum, NodeDatum):
            node_datum = NodeDatum.from_cbor(node_datum.cbor)
        node_pkh = str(VerificationKeyHash(node_datum.node_state.ns_operator))
        node_aggregation_participation = NodeAggregationParticipationCreate(
            aggregation_id=aggregation_id,
            node_pkh=node_pkh,
        )
        await node_aggregation_participation_crud.create(
            db_session=db_session, obj_in=node_aggregation_participation
        )


async def store_reward_distribution(
    db_session: AsyncSession,
    aggregation_id: str,
    input_reward_datum: RewardDatum,
    output_reward_datum: RewardDatum,
) -> None:
    """Store reward distribution."""
    for input_reward, output_reward in zip(
        input_reward_datum.reward_state.node_reward_list,
        output_reward_datum.reward_state.node_reward_list,
    ):
        node_pkh = str(VerificationKeyHash(input_reward.reward_address))
        reward_distribution = RewardDistributionCreate(
            node_pkh=node_pkh,
            total_rewards_available=output_reward.reward_amount,
            aggregation_reward_increase=output_reward.reward_amount
            - input_reward.reward_amount,
            node_aggregation_id=aggregation_id,
        )
        await reward_distribution_crud.create(
            db_session=db_session, obj_in=reward_distribution
        )


async def store_job(
    db_session: AsyncSession,
    feed_id: str,
    schedule: str,
) -> Job:
    """Store job."""
    job = JobCreate(
        feed_id=feed_id,
        schedule=schedule,
    )
    return await jobs_crud.create(db_session=db_session, obj_in=job)


async def store_operational_error(
    db_session: AsyncSession,
    feed_id: str,
    exception: Exception,
) -> None:
    """Store operational error."""
    operational_error = OperationalErrorCreate(
        feed_id=feed_id,
        error_type=type(exception).__name__,
        error_message=str(exception),
        error_context=str(exception.__context__),
        error_traceback=get_traceback_str(exception),
    )
    await operational_errors_crud.create(
        db_session=db_session, obj_in=operational_error
    )


async def delete_unlinked_aggregated_rates_and_flows(
    feed_id: UUID, db_session: AsyncSession
):
    """Delete aggregated rate records older than 24 hours that are not linked to node updates for a specific feed."""
    # Build a subquery for rate aggregation IDs that are linked to node updates
    linked_aggregation_ids = await node_update_crud.get_linked_aggregation_ids(
        feed_id, db_session
    )

    # Subquery to find unlinked aggregation IDs in AggregatedRate table older than 24 hours
    unlinked_aggregation_ids = (
        await aggregated_rate_details_crud.get_unlinked_aggregation_ids(
            linked_aggregation_ids, feed_id, db_session
        )
    )

    # Delete associated entries from rate_data_flow first to maintain referential integrity
    delete_flows_query = (
        await rate_dataflow_crud.delete_rate_data_flow_by_aggregation_id(
            unlinked_aggregation_ids, db_session
        )
    )

    # Now delete entries from AggregatedRate
    delete_rates_query = await aggregated_rate_details_crud.delete_aggregated_rate_details_by_aggregation_id(
        unlinked_aggregation_ids, db_session
    )

    return delete_flows_query, delete_rates_query


async def periodic_cleanup_task(feed_id: UUID):
    """Periodic cleanup task to delete unlinked aggregated rates and flows for a specific feed."""
    while True:
        try:
            # Assuming that get_session() correctly sets up and provides an AsyncSession
            async with get_session() as db_session:
                try:
                    results = await delete_unlinked_aggregated_rates_and_flows(
                        feed_id, db_session
                    )
                    logger.info(
                        "Deleted %s rate data flows and %s aggregated rates for feed %s.",
                        results[0],
                        results[1],
                        feed_id,
                    )
                except Exception as e:  # pylint: disable=broad-except
                    logger.error(
                        "Error during cleanup operation for feed %s: %s",
                        feed_id,
                        str(e),
                    )
                finally:
                    # Ensures that the session is closed after processing
                    await db_session.commit()
        except Exception as e:  # pylint: disable=broad-except
            logger.error("Database session failed for feed %s: %s", feed_id, str(e))
        finally:
            # Wait for 24 hours (86400 seconds) before running again
            logger.info("Waiting for the next cleanup cycle for feed %s.", feed_id)
            await asyncio.sleep(86400)
