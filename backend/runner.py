"""Main updater class"""

import asyncio
import inspect
import logging
import time
from datetime import datetime, timedelta
from math import ceil
from typing import List, Optional, Tuple

from charli3_offchain_core import ChainQuery, Node
from charli3_offchain_core.aggregate_conditions import check_oracle_settings
from charli3_offchain_core.backend import UnsuccessfulResponse
from charli3_offchain_core.datums import (
    AggDatum,
    NodeDatum,
    Nothing,
    OracleDatum,
    PriceData,
    PriceFeed,
    RewardDatum,
)
from charli3_offchain_core.oracle_checks import (
    check_utxo_asset_balance,
    filter_node_datums_by_node_operator,
    get_oracle_datums_only,
    get_oracle_utxos_with_datums,
)
from charli3_offchain_core.utils.exceptions import CollateralException
from pycardano import Address

from backend.api.aggregated_coin_rate import AggregatedCoinRate

from .api import NodeSyncApi
from .db.crud import (
    node_aggregation_crud,
    node_crud,
    node_update_crud,
    transaction_crud,
)
from .db.database import get_session
from .db.models import NodeAggregationCreate, NodeUpdateCreate, TransactionCreate
from .db.service import (
    process_and_store_nodes_data,
    store_node_aggregation_participation,
    store_operational_error,
    store_reward_distribution,
)

logger = logging.getLogger("runner")
logging.Formatter.converter = time.gmtime


class FeedUpdater:
    """Main thread for managing a node feed"""

    def __init__(
        self,
        update_inter: int,
        percent_resolution: int,
        reward_destination_address: str,
        reward_collection_trigger: int,
        node: Node,
        rate: AggregatedCoinRate,
        context: ChainQuery,
        feed_id: Optional[str] = None,
        node_sync_api: Optional[NodeSyncApi] = None,
    ):
        self.update_inter = update_inter
        self.percent_resolution = percent_resolution
        self.reward_destination_address = reward_destination_address
        self.reward_collection_trigger = reward_collection_trigger
        self.node = node
        self.rate = rate
        self.context = context
        self.fee_asset_hash = self.node.c3_token_hash
        self.fee_asset_name = self.node.c3_token_name
        self.oracle_address = self.node.oracle_addr
        self.node_datum: NodeDatum = None
        self.oracle_datum: OracleDatum = None
        self.agg_datum: AggDatum = None
        self.reward_datum: RewardDatum = None
        self.feed_id = feed_id
        self.node_sync_api = node_sync_api

    async def run(self):
        """Checks and if necessary updates and/or aggregates the contract"""
        # async with get_session() as db_session:
        #     await store_job(db_session, self.feed_id, self.update_inter)

        await self.initialize_feed()
        while True:
            start_time = time.time()
            logger.info("Requesting data %s", self.node.pub_key_hash)
            try:
                # Run all of the requests simultaneously
                data_coro = [self.rate.get_aggregated_rate(), self.context.get_utxos()]

                rate_tuple, oracle_utxos = await asyncio.gather(*data_coro)

                rate, aggregated_rate_id = rate_tuple

                # add check to validate the final aggregated rate
                if rate is None or rate <= 0:
                    raise ValueError("Invalid Aggregated Rate")
                # Prepare the rate for uploading
                final_rate = self._calculate_rate(rate)

                # Getting all datums
                (
                    oraclefeed_utxo,
                    aggstate_utxo,
                    reward_utxo,
                    nodes_utxos,
                ) = get_oracle_utxos_with_datums(
                    oracle_utxos,
                    self.node.aggstate_nft,
                    self.node.oracle_nft,
                    self.node.reward_nft,
                    self.node.node_nft,
                )

                self.agg_datum = aggstate_utxo.output.datum
                self.reward_datum = reward_utxo.output.datum
                self.oracle_datum: OracleDatum = oraclefeed_utxo.output.datum
                nodes_datum: List[NodeDatum] = [
                    node.output.datum for node in nodes_utxos
                ]

                # Get the current node datum
                node_own_datum = filter_node_datums_by_node_operator(
                    nodes_datum, self.node.node_operator
                )

                # Prepare the rest of the variables for the checks
                nodes_updated = self.total_nodes_updated(nodes_datum, self.oracle_datum)
                req_nodes = self.agg_datum.aggstate.ag_settings.required_nodes_num()
                fees = self.agg_datum.aggstate.ag_settings.os_node_fee_price
                get_paid = check_utxo_asset_balance(
                    aggstate_utxo,
                    self.fee_asset_hash,
                    self.fee_asset_name,
                    (
                        nodes_updated * fees.node_fee
                        + fees.aggregate_fee
                        + fees.platform_fee
                    ),
                )

                # Logging times.
                data_time = time.time()
                logger.info(
                    "Data gathering took: %s",
                    str(timedelta(seconds=data_time - start_time)),
                    extra={
                        "tag": "data_gathering",
                        "timedelta": timedelta(seconds=data_time - start_time),
                    },
                )
                logger.info(
                    "Nodes updated: %s, Required minimum: %s",
                    str(nodes_updated),
                    str(req_nodes),
                    extra={
                        "tag": "nodes_updated",
                        "nodes_updated": nodes_updated,
                        "req_nodes": req_nodes,
                    },
                )

                # Aggregate, Update or Collect
                called = await self.feed_operate(
                    nodes_updated,
                    req_nodes,
                    final_rate,
                    get_paid,
                    node_own_datum.node_state.ns_feed,
                    aggregated_rate_id,
                )

                # Logging times
                if called:
                    logger.info(
                        "Operation took: %ss",
                        str(timedelta(seconds=time.time() - data_time)),
                        extra={"operation_time": time.time() - data_time},
                    )

            except Exception as exc:
                async with get_session() as db_session:
                    await store_operational_error(
                        db_session,
                        self.feed_id,
                        exc,
                    )
                if isinstance(exc, UnsuccessfulResponse):
                    logger.error(repr(exc))
                elif isinstance(exc, CollateralException):
                    logger.error(
                        "Failed to update or aggregate node due to collateral issue: %s",
                        exc,
                    )
                elif isinstance(exc, ValueError):
                    logger.error(repr(exc))
                else:
                    logger.critical(repr(exc))

            finally:
                time_elapsed = time.time() - start_time
                logger.info("Loop took: %ss", str(timedelta(seconds=time_elapsed)))
                await asyncio.sleep(max(self.update_inter - time_elapsed, 0))

    def _is_collect_needed(self):
        """Determine if a withdrawal is needed based on reward conditions"""

        c3_previous_amount = self._get_previous_node_reward()
        return c3_previous_amount > self.reward_collection_trigger

    def _get_previous_node_reward(self):
        """Reuse the already queried reward datum
        (e.g before aggregate transactions) of the node"""
        # Reuse the previous reward in order to reduces the number of connection
        # with the blockchain.
        return next(
            (
                reward_info.reward_amount
                for reward_info in self.reward_datum.reward_state.node_reward_list
                if reward_info.reward_address == self.node.node_operator
            ),
            0,
        )

    def _required_collect_arguments(self):
        """Check argument availability for automatic process."""
        return (
            self.reward_destination_address != ""
            and self.reward_collection_trigger != 0
        )

    async def _withdraw_rewards(self):
        """Handles the logic for withdrawing rewards."""
        try:
            logger.info("Started automatic node collect")
            await self.node.collect(
                Address.from_primitive(self.reward_destination_address)
            )
            return True
        except ValueError as exc:
            logger.error(repr(exc))
            return False

    async def initialize_feed(self):
        """Check that our feed is initialized and do if its not"""
        logger.info("Initializing feed")

        try:
            oracle_utxos = await self.context.get_utxos()

            _, self.agg_datum, self.reward_datum, nodes_datum = get_oracle_datums_only(
                oracle_utxos,
                self.node.aggstate_nft,
                self.node.oracle_nft,
                self.node.reward_nft,
                self.node.node_nft,
            )

            check_oracle_settings(self.agg_datum.aggstate.ag_settings)

            node_own_datum = filter_node_datums_by_node_operator(
                nodes_datum, self.node.node_operator
            )

            if (
                node_own_datum is None
                or self.agg_datum is None
                or self.reward_datum is None
                or None in nodes_datum
            ):
                logger.critical("One or more relevant datums are missing")

            async with get_session() as db_session:
                await process_and_store_nodes_data(
                    nodes_datum, self.node.network, self.feed_id, db_session
                )
                node_db_object = await node_crud.get_node_by_pkh(
                    str(self.node.pub_key_hash), db_session
                )
                # handle non db cases
                if node_db_object is not None:
                    self.node.id = node_db_object.id
                else:
                    self.node.id = None

            if node_own_datum.node_state.ns_feed == Nothing():
                rate, rate_aggregation_id = await self.rate.get_aggregated_rate()
                final_rate = self._calculate_rate(rate)
                tx_status, tx = await self.node.update(final_rate)

                tx_model = TransactionCreate(
                    node_id=self.node.id,
                    feed_id=self.feed_id,
                    timestamp=datetime.now(),
                    status=tx_status,
                    tx_hash=str(tx.id),
                    tx_fee=tx.transaction_body.fee,
                    tx_body=str(tx.transaction_body),
                )

                node_update = NodeUpdateCreate(
                    node_id=self.node.id,
                    feed_id=self.feed_id,
                    timestamp=datetime.now(),
                    status=tx_status,
                    updated_value=final_rate,
                    rate_aggregation_id=rate_aggregation_id,
                    tx_hash=str(tx.id),
                    trigger="Time_Expiry",
                )

                if self.node_sync_api and node_update:
                    await self.node_sync_api.report_update(node_update)

                async with get_session() as db_session:
                    await transaction_crud.create(
                        db_session=db_session, obj_in=tx_model
                    )
                    await node_update_crud.create(
                        db_session=db_session, obj_in=node_update
                    )

                await asyncio.sleep(60)

        except CollateralException as error:
            logger.error("Failed to initialize node due to collateral issue: %s", error)
        except Exception as error:
            logger.error("An unexpected error occurred: %s", error)

    @staticmethod
    def _calculate_rate(rate):
        return ceil(rate * 1000000)

    def check_rate_change(self, new_rate: int, prev_rate: int) -> bool:
        """check rate change condition"""
        change = round(
            (abs(new_rate - prev_rate) / prev_rate) * self.percent_resolution
        )
        res = change > self.agg_datum.aggstate.ag_settings.os_aggregate_change
        logger.info(
            "check_rate_change: %s by %s  (centi percentage)", str(res), str(change)
        )
        return res

    def node_is_expired(self, last_time: int) -> bool:
        """check time change condition for the node"""
        return self._is_expired(
            last_time, self.agg_datum.aggstate.ag_settings.os_updated_node_time
        )

    def node_consumed_on_last_aggregation(
        self, node_updated_time: int, ofeed_updated_time: PriceData | None
    ) -> bool:
        """
        Check if the oracle feed is newer than the node's updated time.
        This means the node has already consumed, and it should report a new value.

        Returns:
            If the feed is not initialized, the nodes should proceed;
            otherwise, validation is performed.
        """
        if ofeed_updated_time is None:
            return True
        return node_updated_time <= ofeed_updated_time.get_timestamp()

    def agg_is_expired(self, last_time: int) -> bool:
        """check time change condition for the aggregation"""
        return self._is_expired(
            last_time, self.agg_datum.aggstate.ag_settings.os_aggregate_time
        )

    def _is_expired(self, last_time: int, valid_timediff: int):
        time_ms = self.node.chain_query.get_current_posix_chain_time_ms()
        timediff = time_ms - last_time
        res = timediff > valid_timediff
        logger.info(
            "%s: %s by %s ms", inspect.stack()[1].function, str(res), str(timediff)
        )
        return res

    async def perform_update(
        self, rate_from_sources: int, update_reason: str, aggregated_rate_id: str | None
    ) -> bool:
        """
        Perform the node update and handle the result.

        Args:
            rate_from_sources (int): The rate obtained from the data sources.
            update_reason (str): The reason or condition triggering the update.

        Returns:
            bool: True if the update was successful, False otherwise.
        """
        try:
            # Perform the update
            update_result = await self.node.update(rate_from_sources)

            if update_result is None:
                self._log_update_failure()
                return False

            # Save the update and associated transaction details
            await self._save_node_update_and_transaction(
                update_result, aggregated_rate_id, rate_from_sources, update_reason
            )

            return True

        except Exception as e:
            logger.error("Update failed: %s", str(e))
            return False

    async def perform_aggregation(
        self, nodes_updated: int, aggregate_reason: str
    ) -> bool:
        """
        Perform the aggregation operation and save the results.

        Args:
            nodes_updated (int): The number of updated nodes involved in the aggregation.
            aggregate_reason (str): The reason or condition triggering the aggregation.

        Returns:
            bool: True if the aggregation was successful, False otherwise.
        """
        try:
            # Perform the aggregation
            aggregate_response = await self.node.aggregate()

            if aggregate_response is None:
                self._log_aggregation_failure()
                return False

            # Save the aggregation and associated transaction details
            await self._save_aggregation_and_transaction(
                nodes_updated, aggregate_response, aggregate_reason
            )

            # Update the oracle feed information
            await self.update_oracle_feed_information()

            # Aggregation was successful
            return True
        except Exception as e:
            logger.error("Aggregation failed: %s", str(e))
            return False

    def timestamp_to_asc(self, timest):
        """transform timestamp on logger readable format"""
        return str(
            datetime.utcfromtimestamp(timest / 1000).strftime("%Y-%m-%dT%H:%M:%S%z")
        )

    def total_nodes_updated(
        self, nodes_datum: list[NodeDatum], oracle_datum: OracleDatum
    ) -> int:
        """Check total nodes updated after last Aggregation"""

        # Remove all uninitialized nodes
        initialized_nodes_datum = list(
            filter(lambda x: x.node_state.ns_feed != Nothing(), nodes_datum)
        )

        total_updated = len(initialized_nodes_datum)

        if not oracle_datum.price_data:
            return total_updated

        oracle_feed_generation_time = oracle_datum.price_data.get_timestamp()
        current_time_ms = self.node.chain_query.get_current_posix_chain_time_ms()

        for node_datum in initialized_nodes_datum:
            last_update_time = node_datum.node_state.ns_feed.df.df_last_update
            time_since_feed_generation = last_update_time - oracle_feed_generation_time
            time_since_last_update = current_time_ms - last_update_time

            if (
                0 > time_since_feed_generation
                or time_since_last_update
                > self.agg_datum.aggstate.ag_settings.os_updated_node_time
            ):
                total_updated -= 1

        return total_updated

    def _log_aggregation_failure(self):
        logger.warning("Failed to aggregate oracle feed despite contract conditions")

    def _log_update_failure(self):
        logger.warning("Failed to update node despite contract conditions")

    async def update_oracle_feed_information(self):
        """Query the updated oracle feed UTXOs after successful aggregation"""
        utxos = await self.context.get_utxos()
        updated_oraclefeed_utxo, *_ = get_oracle_utxos_with_datums(
            utxos,
            self.node.aggstate_nft,
            self.node.oracle_nft,
            self.node.reward_nft,
            self.node.node_nft,
        )
        # Update the oracle feed information
        self.oracle_datum: OracleDatum = updated_oraclefeed_utxo.output.datum

    def _should_aggregate_conditions(
        self, new_rate: int, oracle_feed: PriceData | None, sufficient_rewards: bool
    ) -> Tuple[bool, str]:
        """
        Determines if the node can aggregate based on the oracle feed and rate change.

        Returns:
            A tuple containing a boolean indicating if aggregation can occur and
            a string indicating the trigger reason ('time_expiry', 'rate_change', or '').
        """
        if not sufficient_rewards:
            return False, "Insufficient_Rewards"

        if not oracle_feed:
            return True, "Initial_Feed_Value"

        if self.check_rate_change(new_rate, oracle_feed.get_price()):
            return True, "Rate_Change"

        if self.agg_is_expired(oracle_feed.get_timestamp()):
            return True, "Time_Expiry"

        return False, "Conditions not met for aggregation"

    def _should_wait_for_optimal_update(
        self, oracle_feed: PriceData | None
    ) -> Tuple[bool, str]:
        """Determines whether the node should wait before updating, based on time until the next scheduled aggregation."""

        if oracle_feed is None:
            logger.warning(
                "Oracle feed data is missing; cannot determine optimal update time."
            )
            return False, "Oracle feed data missing"

        aggregation_interval = self.agg_datum.aggstate.ag_settings.os_aggregate_time
        current_time_ms = self.node.chain_query.get_current_posix_chain_time_ms()
        next_agg_time_ms = oracle_feed.get_timestamp() + aggregation_interval
        time_until_next_agg_ms = next_agg_time_ms - current_time_ms
        time_until_next_agg_mins = time_until_next_agg_ms / (60 * 1000)

        MAX_THRESHOLD_OFFSET_MS = 15 * 60 * 1000
        threshold_offset_ms = min(aggregation_interval / 3, MAX_THRESHOLD_OFFSET_MS)

        should_wait = time_until_next_agg_ms > threshold_offset_ms
        logger.info("---------------------------------------")
        logger.info(
            "Next scheduled aggregation expected in: %.2f minutes.",
            time_until_next_agg_mins,
        )
        logger.info(
            "Allowed update window: %.2f minutes.", threshold_offset_ms / (60 * 1000)
        )
        logger.info("---------------------------------------")
        if should_wait:
            logger.info(
                "Waiting for optimal update timing that is closer to the next scheduled aggregation."
            )
            return True, "There's still time until the next aggregation."
        else:
            logger.info("Next scheduled aggregation is approaching soon.")
            return False, "Next scheduled aggregation is approaching soon."

    def _should_update_conditions(
        self,
        own_feed: PriceFeed | Nothing,
        new_rate: int,
        oracle_feed: PriceData | None,
        sufficient_rewards: bool,
    ) -> Tuple[bool, str]:
        """Determines if the node should update its feed."""

        if not sufficient_rewards:
            return False, "Insufficient_rewards"

        if own_feed == Nothing():
            return True, "Feed_Initialization"

        if self.check_rate_change(new_rate, own_feed.df.df_value):
            return True, "Rate_Change"

        should_wait, _ = self._should_wait_for_optimal_update(oracle_feed)

        if should_wait:
            return False, "Waiting_For_Optimal_Update_Time"

        if self.node_is_expired(own_feed.df.df_last_update):
            return True, "Time_Expiry"

        if self.node_consumed_on_last_aggregation(
            own_feed.df.df_last_update, oracle_feed
        ):
            logger.info("Proceeding with node update...")
            return True, "Feed time exceeds node time"

        logger.info("Update not required; last update is still valid.")
        return False, "Node update not required."

    async def _save_node_update_and_transaction(
        self,
        update_result,
        aggregated_rate_id,
        new_rate,
        update_reason,
    ):
        tx_status, tx = update_result
        tx_model = TransactionCreate(
            node_id=self.node.id,
            feed_id=self.feed_id,
            timestamp=datetime.now(),
            status=tx_status,
            tx_hash=str(tx.id),
            tx_fee=tx.transaction_body.fee,
            tx_body=str(tx.transaction_body),
        )

        node_update = NodeUpdateCreate(
            node_id=self.node.id,
            feed_id=self.feed_id,
            timestamp=datetime.now(),
            status=tx_status,
            updated_value=new_rate,
            rate_aggregation_id=aggregated_rate_id,
            tx_hash=str(tx.id),
            trigger=update_reason,
        )

        if self.node_sync_api and node_update:
            await self.node_sync_api.report_update(node_update)

        async with get_session() as db_session:
            await transaction_crud.create(db_session=db_session, obj_in=tx_model)
            await node_update_crud.create(db_session=db_session, obj_in=node_update)

    async def _save_aggregation_and_transaction(
        self, nodes_updated, aggregate_result, agg_reason
    ):
        (
            agg_value,
            valid_nodes,
            output_reward_datum,
            tx_status,
            tx,
        ) = aggregate_result

        agg_model = NodeAggregationCreate(
            node_pkh=str(self.node.pub_key_hash),
            feed_id=self.feed_id,
            timestamp=datetime.now(),
            status=tx_status,
            aggregated_value=agg_value,
            nodes_count=nodes_updated,
            tx_hash=str(tx.id),
            trigger=agg_reason,
        )

        tx_model = TransactionCreate(
            node_id=self.node.id,
            feed_id=self.feed_id,
            timestamp=datetime.now(),
            status=tx_status,
            tx_hash=str(tx.id),
            tx_fee=tx.transaction_body.fee,
            tx_body=str(tx.transaction_body),
        )

        async with get_session() as db_session:
            await transaction_crud.create(db_session=db_session, obj_in=tx_model)
            node_agg = await node_aggregation_crud.create(
                db_session=db_session, obj_in=agg_model
            )
            await store_node_aggregation_participation(
                db_session,
                node_agg.id,
                valid_nodes,
            )
            await store_reward_distribution(
                db_session,
                node_agg.id,
                self.reward_datum,
                output_reward_datum,
            )

    async def feed_operate(
        self,
        nodes_updated: int,
        minimum_required_nodes: int,
        rate_from_sources: int,
        sufficient_rewards: bool,
        own_feed: PriceFeed,
        aggregated_rate_id: Optional[str] = None,
    ) -> bool:
        """
        Primary logic for determining aggregate, update, and collect transactions.

        Args:
            nodes_updated (int): Number of nodes updated.
            minimum_required_nodes (int): Minimum number of nodes required for aggregation.
            rate_from_sources (int): The rate obtained from the sources.
            sufficient_rewards (bool): Whether there are sufficient rewards.
            own_feed (PriceFeed): The current feed data of the node.
            aggregated_rate_id (Optional[str]): ID of the aggregated rate, if any.

        Returns:
            bool: True if an operation was performed, False otherwise.
        """
        try:
            # Determine if aggregation should proceed based on conditions
            should_aggregate, aggregate_reason = self._should_aggregate_conditions(
                rate_from_sources, self.oracle_datum.price_data, sufficient_rewards
            )

            # Determines if the node should update its feed
            should_update, update_reason = self._should_update_conditions(
                own_feed,
                rate_from_sources,
                self.oracle_datum.price_data,
                sufficient_rewards,
            )
            if should_update:
                return await self.perform_update(
                    rate_from_sources, update_reason, aggregated_rate_id
                )

            # Check if enough nodes have been updated to allow aggregation
            if nodes_updated >= minimum_required_nodes and should_aggregate:
                if await self.perform_aggregation(nodes_updated, aggregate_reason):
                    return True  # Aggregation performed

            if self._required_collect_arguments() and self._is_collect_needed():
                if await self._withdraw_rewards():
                    return True  # Collected withdraws

            return False  # No operation performed
        except Exception as e:
            logger.error("Operation failed %s", str(e))
            return False
