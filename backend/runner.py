"""Main updater class"""
from datetime import timedelta, datetime
import time
import asyncio
import logging
import inspect
from math import ceil

from .api import NodeContractApi, CoinRate, ChainQuery
from .api.api import UnsuccessfulResponse
from .api.datums import Feed, NodeDatum, OracleDatum
from .api.node import FailedOperation, PABTimeout
from .core.oracle import OracleSettings

logger = logging.getLogger("runner")
logging.Formatter.converter = time.gmtime

class FeedUpdater():
    """Main thread for managing a node feed"""
    def __init__(self,
                 update_inter: int,
                 oracle_settings: OracleSettings,
                 node: NodeContractApi,
                 rate: CoinRate,
                 chain: ChainQuery):
        self.update_inter = update_inter
        self.oracle_settings = oracle_settings
        self.node = node
        self.rate = rate
        self.chain = chain
        self.node_nft = self.node.oracle.get_node_feed_nft()
        self.oracle_nft = self.node.oracle.get_oracle_feed_nft()
        self.aggstate_nft = self.node.oracle.get_aggstate_nft()
        self.fee_asset = self.node.oracle.get_fee_asset()
        self.oracle_address = self.node.oracle.get_oracle_address()
        self.node_datum = None
        self.oracle_datum = None

    async def run(self):
        """Checks and if necesary updates and/or aggregates the contract"""
        await self.node.activate()
        await self.initialize_feed()
        while True:
            start_time = time.time()
            logger.info("Requesting data")
            try:
                # Run all of the requests simultaneously
                data_coro = [
                    self.rate.get_rate(),
                    self.chain.get_nodes_datum(self.node_nft),
                    self.chain.get_oracle_datum(self.oracle_nft),
                    self.chain.get_feed_balance(self.aggstate_nft, self.fee_asset)
                ]

                data = await asyncio.gather(*data_coro)

                # Prepare the rate for uploading
                new_rate = self._calculate_rate(data[0])
                # Get the current node datum
                node_own_datum = self.get_node_info(data[1], self.node.pkh)

                #Logs own datum information
                if self.node_datum:
                    if self.node_datum.node_feed.timestamp < node_own_datum.node_feed.timestamp:
                        previous = self.node_datum
                        self.node_datum = node_own_datum
                        logger.info('Updating Feed Runner Own Datum',
                            extra={'tag':'node_own_datum',
                            'context':'datum_update',
                            'feed_value':node_own_datum.node_feed.value,
                            'expires_on':
                            self.timestamp_to_asc(
                                self.node_datum.node_feed.timestamp +
                                self.oracle_settings.node_expiry
                            ),
                            'datum_timestamp':self.timestamp_to_asc(
                                self.node_datum.node_feed.timestamp),
                            'datum_timestamp_prev':self.timestamp_to_asc(
                                self.node_datum.node_feed.timestamp),
                            'feed_value_prev':previous.node_feed.value,
                            'datum_delta':self.node_datum.node_feed.timestamp
                            - previous.node_feed.timestamp
                            })
                else:
                    self.node_datum = node_own_datum
                    logger.info('Updating Feed Runner Own Datum',extra={'tag':'node_own_datum',
                    'context':'runner init',
                    'feed_value':self.node_datum.node_feed.value,
                    'datum_timestamp':self.timestamp_to_asc(
                        self.node_datum.node_feed.timestamp),
                    'expires_on':self.timestamp_to_asc(
                        self.node_datum.node_feed.timestamp + self.oracle_settings.node_expiry)})

                # Remove all uninitialized nodes
                nodes_datum = list(filter(
                    lambda x: x.node_feed.has_value(),
                    data[1]
                ))
                # We remove our node because it has to pass more checks than the
                # rest. We assume that it doesn't when counting valid nodes.
                nodes_datum.remove(node_own_datum)

                # Prepare the rest of the variables for the checks
                oracle_datum = data[2]
                own_feed = node_own_datum.node_feed
                nodes_updated = self.total_nodes_updated(
                    nodes_datum,
                    oracle_datum)
                req_nodes = self.oracle_settings.required_nodes_num()
                node_fee = self.oracle_settings.node_fee
                feed_balance = data[3]

                if self.oracle_datum:
                    if self.oracle_datum.oracle_feed.timestamp < oracle_datum.oracle_feed.timestamp:
                        previous = self.oracle_datum
                        self.oracle_datum = oracle_datum
                        logger.info('Updating Feed Runner Oracle Datum',
                        extra={'tag':'oracle_datum',
                            'context':'datum_update',
                            'feed_value':oracle_datum.oracle_feed.value,
                            'expires_on':self.timestamp_to_asc(
                                self.oracle_datum.oracle_feed.timestamp
                                + self.oracle_settings.node_expiry),
                            'datum_timestamp':self.timestamp_to_asc(
                                self.oracle_datum.oracle_feed.timestamp),
                            'datum_timestamp_prev':self.timestamp_to_asc(
                                previous.oracle_feed.timestamp),
                            'feed_value_prev': previous.oracle_feed.value,
                            'datum_delta':self.oracle_datum.oracle_feed.timestamp
                                - previous.oracle_feed.timestamp
                            })

                else:
                    self.oracle_datum = oracle_datum
                    logger.info('Updating Feed Runner Oracle Datum',extra={'tag':'oracle_datum',
                    'context':'runner init',
                    'feed_value':oracle_datum.oracle_feed.value,
                    'datum_timestamp':self.timestamp_to_asc(oracle_datum.oracle_feed.timestamp),
                    'expires_on':self.timestamp_to_asc(
                        oracle_datum.oracle_feed.timestamp + self.oracle_settings.node_expiry)})

                # Logging times.
                data_time = time.time()
                logger.info(
                    "Data gathering took: %s",
                    str(timedelta(seconds=data_time-start_time)),
                    extra={
                    'tag': 'data_gathering','timedelta':timedelta(seconds=data_time-start_time)}
                )
                logger.info(
                    "Nodes updated: %s from %s",
                    str(nodes_updated),
                    str(req_nodes),
                    extra={
                    'tag': 'nodes_updated','nodes_updated':nodes_updated,'req_nodes':req_nodes}
                )

                # Update - Aggregate or Update Aggregate
                called = await self.feed_operate(
                    nodes_updated,
                    req_nodes,
                    new_rate,
                    feed_balance,
                    node_fee,
                    own_feed,
                    oracle_datum.oracle_feed
                )

                # Logging times
                if called:
                    logger.info(
                        "Operation took: %ss",
                        str(timedelta(seconds=time.time()-data_time)),
                        extra={'operation_time':time.time()-data_time}
                    )

            except (UnsuccessfulResponse) as exc:
                logger.error(repr(exc))

            except (FailedOperation, PABTimeout) as exc:
                await self.node.re_activate()
                logger.error(repr(exc))

            except Exception as exc:
                logger.critical(repr(exc))

            time_elapsed = time.time()-start_time
            logger.info(
                "Loop took: %ss",
                str(timedelta(seconds=time_elapsed))
            )
            await asyncio.sleep(max(self.update_inter-time_elapsed, 0))

    async def initialize_feed(self):
        """Check that our feed is initialized and do if its not"""
        logger.info("Initializing feed")
        datums = await self.chain.get_nodes_datum(self.node_nft)
        own_datum = self.get_node_info(datums, self.node.pkh)
        if not own_datum.node_feed.has_value():
            rate = await self.rate.get_rate()
            await self.node.update(self._calculate_rate(rate))
            await asyncio.sleep(60)

    @staticmethod
    def _calculate_rate(rate):
        return ceil(rate*1000000)

    def check_feed_has_balance(
        self,
        feed_balance,
        node_fee,
        nodes_updated
    ) -> bool:
        """Validates if feed balance is enough in order to pay next update"""
        logger.info("Feed Balance: Funds available on feed %s", feed_balance, extra={
                    'tag': 'feed_balance','feed_balance': feed_balance,
                    'node_fee':node_fee, 'node_fee*nodes_updated':node_fee*nodes_updated,
                    'feed_balance_available':feed_balance-node_fee*nodes_updated})

        return node_fee*nodes_updated < feed_balance

    def check_rate_change(
            self,
            new_rate: int,
            prev_rate: int) -> bool:
        """check rate change condition"""
        res = self.oracle_settings.percent_resolution
        change = abs((new_rate*res)/prev_rate-res)
        res = change > self.oracle_settings.aggregate_change
        logger.info(
            "check_rate_change: %s by %s",
            str(res),
            str(change)
        )
        return res

    def node_is_expired(
            self,
            last_time: int) -> bool:
        """check time change condition for the node"""
        return self._is_expired(last_time, self.oracle_settings.node_expiry)

    def agg_is_expired(
            self,
            last_time: int) -> bool:
        """check time change condition for the aggregation"""
        return self._is_expired(last_time, self.oracle_settings.aggregate_time)

    def _is_expired(self, last_time, valid_time):
        time_ms = time.time_ns()*1e-6
        timediff = time_ms-last_time
        res = timediff > valid_time
        logger.info(
            "%s: %s by %s",
            inspect.stack()[1].function,
            str(res),
            str(timediff)
        )
        return res

    def timestamp_to_asc(self, timest):
        """transform timestamp on logger readeable format"""
        return str(datetime.utcfromtimestamp(timest/1000).strftime('%Y-%m-%dT%H:%M:%S%z'))

    def total_nodes_updated(
            self,
            nodes_datum: list[NodeDatum],
            oracle_datum: OracleDatum) -> int:
        """check total nodes updated after last Aggregation"""
        updated = len(nodes_datum)
        ofeed = oracle_datum.oracle_feed
        time_ms = time.time_ns()*1e-6
        if ofeed.has_value():
            for dat in nodes_datum:
                timediff = dat.node_feed.timestamp - ofeed.timestamp
                delta_update = time_ms - dat.node_feed.timestamp
                if not (0 < timediff
                        and delta_update < self.oracle_settings.node_expiry):
                    updated -= 1
        return updated

    def get_node_info(
            self,
            nodes_datum: list[NodeDatum],
            pkh: str) -> NodeDatum:
        """get node's last update information."""
        for dat in nodes_datum:
            if dat.node_operator == pkh:
                return dat
        return None

    async def feed_operate(self,
                           nodes_updated: int,
                           req_nodes: int,
                           new_rate: int,
                           feed_balance: int,
                           node_fee: int,
                           own_feed: Feed,
                           oracle_feed: Feed):
        """Main logic of the runnner"""

        can_aggregate = (not oracle_feed.has_value() or
                          (self.check_rate_change(new_rate, oracle_feed.value)
                           or self.agg_is_expired(oracle_feed.timestamp)))

        get_paid = self.check_feed_has_balance(feed_balance,node_fee,nodes_updated+1)

        if (self.check_rate_change(new_rate, own_feed.value)
                or self.node_is_expired(own_feed.timestamp)) and get_paid :

            # Our node is not updated
            if (nodes_updated >= req_nodes-1) and can_aggregate:
                # Our update is the one missing for an aggregate
                await self.node.update_aggregate(new_rate)
            else:
                # More nodes are required before aggregating
                await self.node.update(new_rate)
        elif (nodes_updated+1 >= req_nodes) and can_aggregate and get_paid :
            # Our node is updated
            await self.node.aggregate()
        else:
            return False
        return True
