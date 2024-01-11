"""Main updater class"""
from datetime import timedelta, datetime
from typing import List
import time
import asyncio
import logging
import inspect
from math import ceil

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

from .api import AggregatedCoinRate
from .api.api import UnsuccessfulResponse

logger = logging.getLogger("runner")
logging.Formatter.converter = time.gmtime


class FeedUpdater:
    """Main thread for managing a node feed"""

    def __init__(
        self,
        update_inter: int,
        percent_resolution: int,
        node: Node,
        rate: AggregatedCoinRate,
        context: ChainQuery,
    ):
        self.update_inter = update_inter
        self.percent_resolution = percent_resolution
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

    async def run(self):
        """Checks and if necesary updates and/or aggregates the contract"""
        await self.initialize_feed()
        while True:
            start_time = time.time()
            logger.info("Requesting data %s", self.node.pub_key_hash)
            try:
                # Run all of the requests simultaneously
                data_coro = [self.rate.get_aggregated_rate(), self.context.get_utxos()]

                rate, oracle_utxos = await asyncio.gather(*data_coro)

                # add check to validate the final aggregated rate
                if rate is None or rate <= 0:
                    raise ValueError("Invalid Aggregated Rate")
                # Prepare the rate for uploading
                new_rate = self._calculate_rate(rate)

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

                # Update - Aggregate or Update Aggregate
                called = await self.feed_operate(
                    nodes_updated,
                    req_nodes,
                    new_rate,
                    get_paid,
                    node_own_datum.node_state.ns_feed,
                    oracle_datum.price_data,
                )

                # Logging times
                if called:
                    logger.info(
                        "Operation took: %ss",
                        str(timedelta(seconds=time.time() - data_time)),
                        extra={"operation_time": time.time() - data_time},
                    )

            except UnsuccessfulResponse as exc:
                logger.error(repr(exc))

            except ValueError as exc:
                logger.error(repr(exc))

            except Exception as exc:
                logger.critical(repr(exc))

            time_elapsed = time.time() - start_time
            logger.info("Loop took: %ss", str(timedelta(seconds=time_elapsed)))
            await asyncio.sleep(max(self.update_inter - time_elapsed, 0))

    async def initialize_feed(self):
        """Check that our feed is initialized and do if its not"""
        logger.info("Initializing feed")

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

        if node_own_datum.node_state.ns_feed == Nothing():
            rate = await self.rate.get_aggregated_rate()
            await self.node.update(self._calculate_rate(rate))
            await asyncio.sleep(60)

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

    async def feed_operate(
        self,
        nodes_updated: int,
        req_nodes: int,
        new_rate: int,
        get_paid: bool,
        own_feed: PriceFeed,
        oracle_feed: PriceData | None,
    ):
        """Main logic of the runnner"""

        can_aggregate = not oracle_feed or (
            self.check_rate_change(new_rate, oracle_feed.get_price())
            or self.agg_is_expired(oracle_feed.get_timestamp())
        )

        if not get_paid:
            logger.warning("Not enough funds available at the contract to pay rewards.")

        if self.check_rate_change(
            new_rate, own_feed.df.df_value
        ) or self.node_is_expired(own_feed.df.df_last_update):
            # Our node is not updated
            # More nodes are required before aggregating
            await self.node.update(new_rate)
        elif (nodes_updated + 1 >= req_nodes) and can_aggregate:
            # Our node is updated
            await self.node.aggregate()
        else:
            return False
        return True
