"""Syncing with Charli3 Central DB."""

import logging
import time
from typing import List, Optional

from charli3_offchain_core import Node
from charli3_offchain_core.backend import Api, ApiResponse

from ..db.crud import (
    aggregated_rate_details_crud,
    feed_crud,
    node_crud,
    rate_dataflow_crud,
)
from ..db.database import get_session
from ..db.models import Feed, NodeUpdate, Provider

logger = logging.getLogger("node_sync_api")
logging.Formatter.converter = time.gmtime


class NodeSyncApi(Api):
    """Class to interact with the NodeSync API."""

    def __init__(self, api_url: Optional[str] = None):
        self.api_url = api_url

    async def report_initialization(
        self,
        feed: Feed,
        node: Node,
        providers: List[Provider],
    ) -> ApiResponse:
        """Report feed and node initialization data to the central db."""
        # Convert providers to a format suitable for JSON serialization with correct casing
        try:
            providers_data = []
            for provider in providers:
                # Assuming you have a method to convert model instances to dict with correct keys
                provider_data = {
                    "providerId": str(provider.id),
                    "feedAddress": feed.feed_address,
                    "name": provider.name,
                    "apiUrl": provider.api_url,
                    "path": provider.path,
                    "token": provider.token,
                    "adapterType": provider.adapter_type,
                }
                providers_data.append(provider_data)

            # Prepare the feed and node data with correct casing
            feed_data = {
                "feedAddress": feed.feed_address,
                "symbol": feed.title,
                "aggStateNFT": feed.aggstate_nft,
                "oracleNFT": feed.oracle_nft,
                "rewardNFT": feed.reward_nft,
                "nodeNFT": feed.node_nft,
                "oracleMintingCurrency": feed.oracle_currency,
            }

            node_data = {
                "pubKeyHash": str(node.pub_key_hash),
                "nodeOperatorAddress": str(node.address),
                "feedAddress": feed.feed_address,
            }

            # Prepare the data payload with corrected key casing
            data = {
                "feed": feed_data,
                "node": node_data,
                "providers": providers_data,
            }

            path = "/api/node-updater/initialize"
            response = await self._post(path=path, data=data)
            logger.info("Successfully reported initialization: %s", response)
        except Exception as e:
            logger.error("Failed to report initialization: %s", e)

    async def report_update(
        self,
        node_update: NodeUpdate,
    ) -> ApiResponse:
        """Report node update data to the central db."""
        try:
            path = "/api/node-updater/reportAll"

            # Fetch rate_data_flow and aggregated_rate_details based on node_update info
            async with get_session() as db_session:
                # Assuming rate_aggregation_id is part of node_update
                rate_aggregation_id = node_update.rate_aggregation_id
                feed = await feed_crud.get(
                    id=node_update.feed_id, db_session=db_session
                )
                node = await node_crud.get(
                    id=node_update.node_id, db_session=db_session
                )

                # Fetch RateDataFlow entries based on rate_aggregation_id
                rate_data_flow_entries = (
                    await rate_dataflow_crud.get_rate_data_flow_by_aggregation_id(
                        rate_aggregation_id, db_session
                    )
                )

                # Fetch AggregatedRateDetails entry based on rate_aggregation_id
                aggregated_rate_details_entry = await aggregated_rate_details_crud.get(
                    id=rate_aggregation_id, db_session=db_session
                )

            # Prepare rate_data_flow for the report
            rate_data_flow_list = [
                {
                    "providerId": str(entry.provider_id),
                    "feedAddress": feed.feed_address,
                    "requestTimestamp": entry.request_timestamp.timestamp(),
                    "symbol": entry.symbol,
                    "responseCode": entry.response_code,
                    "responseBody": entry.response_body,
                    "rate": float(entry.rate) if entry.rate else None,
                    "rateType": entry.rate_type,
                    "rateAggregationId": (
                        str(entry.rate_aggregation_id)
                        if entry.rate_aggregation_id
                        else None
                    ),
                }
                for entry in rate_data_flow_entries
            ]

            # Prepare aggregated_rate_details for the report
            aggregated_rate_details = {
                "feedAddress": feed.feed_address,
                "requestedAt": aggregated_rate_details_entry.requested_at.timestamp(),
                "aggregationTimestamp": aggregated_rate_details_entry.aggregation_timestamp.timestamp(),
                "aggregatedRate": (
                    float(aggregated_rate_details_entry.aggregated_rate)
                    if aggregated_rate_details_entry.aggregated_rate
                    else None
                ),
                "method": aggregated_rate_details_entry.method,
            }

            # Construct the node_update dict
            node_update_dict = {
                "txHash": node_update.tx_hash,
                "nodeAddress": node.node_operator_address,
                "feedAddress": feed.feed_address,
                "timestamp": node_update.timestamp.timestamp(),
                "status": node_update.status,
                "updatedValue": node_update.updated_value,
                "rateAggregationId": str(node_update.rate_aggregation_id),
                "trigger": node_update.trigger,
            }

            # Full data payload
            data = {
                "nodeUpdate": node_update_dict,
                "rateDataFlow": rate_data_flow_list,
                "aggregatedRateDetails": aggregated_rate_details,
            }
            response = await self._post(path=path, data=data)
            logger.info("Successfully reported node update: %s", response)
            return response

        except Exception as e:
            logger.error("Failed to report node update: %s", e, exc_info=True)
