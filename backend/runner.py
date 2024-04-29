"""Main updater class"""

from datetime import timedelta, datetime
from typing import List, Optional, Tuple
import time
import asyncio
import logging
import inspect
from math import ceil
from pycardano import Address

from charli3_offchain_core import Node, ChainQuery
from charli3_offchain_core.datums import (
    PriceFeed,
    PriceData,
    NodeDatum,
    OracleDatum,
    Nothing,
    AggDatum,
    RewardDatum,
)
from charli3_offchain_core.oracle_checks import (
    filter_node_datums_by_node_operator,
    get_oracle_utxos_with_datums,
    check_utxo_asset_balance,
    get_oracle_datums_only,
)
from charli3_offchain_core.aggregate_conditions import check_oracle_settings
from charli3_offchain_core.utils.exceptions import CollateralException

from .api import AggregatedCoinRate, NodeSyncApi
from .api.providers.api import UnsuccessfulResponse
from .db.database import get_session
from .db.service import (
    process_and_store_nodes_data,
    store_node_aggregation_participation,
    store_reward_distribution,
    store_job,
    store_operational_error,
)
from .db.crud import (
    node_crud,
    node_update_crud,
    transaction_crud,
    node_aggregation_crud,
)
from .db.models import (
    NodeUpdateCreate,
    TransactionCreate,
    NodeAggregationCreate,
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
        """Checks and if necesary updates and/or aggregates the contract"""
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
                oracle_datum: OracleDatum = oraclefeed_utxo.output.datum
                nodes_datum: List[NodeDatum] = [
                    node.output.datum for node in nodes_utxos
                ]

                # Get the current node datum
                node_own_datum = filter_node_datums_by_node_operator(
                    nodes_datum, self.node.node_operator
                )

                # Remove all uninitialized nodes

                valid_nodes_datum = list(
                    filter(lambda x: x.node_state.ns_feed != Nothing(), nodes_datum)
                )

                # Prepare the rest of the variables for the checks

                nodes_updated = self.total_nodes_updated(
                    valid_nodes_datum, oracle_datum
                )
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
                    "Nodes updated: %s from %s",
                    str(nodes_updated),
                    str(req_nodes),
                    extra={
                        "tag": "nodes_updated",
                        "nodes_updated": nodes_updated,
                        "req_nodes": req_nodes,
                    },
                )

                # Update or Aggregate
                called = await self.feed_operate(
                    nodes_updated,
                    req_nodes,
                    final_rate,
                    get_paid,
                    node_own_datum.node_state.ns_feed,
                    oracle_datum.price_data,
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
        # with the blokchain.
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
        except ValueError as exc:
            logger.error(repr(exc))

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

    def agg_is_expired(self, last_time: int) -> bool:
        """check time change condition for the aggregation"""
        return self._is_expired(
            last_time, self.agg_datum.aggstate.ag_settings.os_aggregate_time
        )

    def _is_expired(self, last_time, valid_time):
        time_ms = time.time_ns() * 1e-6
        timediff = int(time_ms - last_time)
        res = timediff > valid_time
        logger.info(
            "%s: %s by %s ms", inspect.stack()[1].function, str(res), str(timediff)
        )
        return res

    def timestamp_to_asc(self, timest):
        """transform timestamp on logger readeable format"""
        return str(
            datetime.utcfromtimestamp(timest / 1000).strftime("%Y-%m-%dT%H:%M:%S%z")
        )

    def total_nodes_updated(
        self, nodes_datum: list[NodeDatum], oracle_datum: OracleDatum
    ) -> int:
        """check total nodes updated after last Aggregation"""
        updated = len(nodes_datum)
        ofeed = oracle_datum.price_data
        time_ms = time.time_ns() * 1e-6
        if ofeed:
            for dat in nodes_datum:
                if dat.node_state.ns_feed == Nothing():
                    updated -= 1
                else:
                    timediff = (
                        dat.node_state.ns_feed.df.df_last_update - ofeed.get_timestamp()
                    )
                    delta_update = time_ms - dat.node_state.ns_feed.df.df_last_update

                    if not (
                        0 < timediff
                        and delta_update
                        < self.agg_datum.aggstate.ag_settings.os_updated_node_time
                    ):
                        updated -= 1
        return updated

    def _can_aggregate(
        self, new_rate: int, oracle_feed: PriceData | None
    ) -> Tuple[bool, str]:
        """
        Determines if the node can aggregate based on the oracle feed and rate change.

        Returns:
            A tuple containing a boolean indicating if aggregation can occur and
            a string indicating the trigger reason ('time_expiry', 'rate_change', or '').
        """
        if not oracle_feed:
            # If there's no oracle feed, aggregation can't proceed.
            return False, ""

        current_price = oracle_feed.get_price()
        timestamp = oracle_feed.get_timestamp()

        # Check for rate change
        if self.check_rate_change(new_rate, current_price):
            return True, "Rate_Change"

        # Check for time expiry
        if self.agg_is_expired(timestamp):
            return True, "Time_Expiry"

        # If none of the conditions are met, return False and an empty reason.
        return False, ""

    def should_update(self, own_feed: PriceFeed, new_rate: int) -> Tuple[bool, str]:
        """Determines if the node should update its feed."""
        if self.check_rate_change(new_rate, own_feed.df.df_value):
            return True, "Rate_Change"
        elif self.node_is_expired(own_feed.df.df_last_update):
            return True, "Time_Expiry"
        return False, "None"

    async def feed_operate(
        self,
        nodes_updated: int,
        req_nodes: int,
        new_rate: int,
        get_paid: bool,
        own_feed: PriceFeed,
        oracle_feed: PriceData | None,
        aggregated_rate_id: Optional[str] = None,
    ) -> bool:
        """Main logic of the runnner"""
        try:
            can_aggregate, agg_reason = self._can_aggregate(new_rate, oracle_feed)

            if not get_paid:
                logger.warning(
                    "Not enough funds available at the contract to pay rewards."
                )
                return False

            # Determines if the node should update its feed
            should_update, update_reason = self.should_update(own_feed, new_rate)

            if should_update:
                tx_status, tx = await self.node.update(new_rate)
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
                    await transaction_crud.create(
                        db_session=db_session, obj_in=tx_model
                    )
                    await node_update_crud.create(
                        db_session=db_session, obj_in=node_update
                    )
            elif (nodes_updated + 1 >= req_nodes) and can_aggregate:
                (
                    agg_value,
                    valid_nodes,
                    output_reward_datum,
                    tx_status,
                    tx,
                ) = await self.node.aggregate()

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
                    await transaction_crud.create(
                        db_session=db_session, obj_in=tx_model
                    )
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

            elif self._required_collect_arguments() and self._is_collect_needed():
                await self._withdraw_rewards()
            else:
                return False
            return True

        except Exception as e:
            logger.error("Operation failed %s", str(e))
            return False
