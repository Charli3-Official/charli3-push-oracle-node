"""Test for backend runner"""
from datetime import datetime
from test.helper.mocked_data import (
    MOCKED_COLLECTION_TRIGGER,
    MOCKED_DESTINATION_ADDRESS,
    MOCKED_PERCENT_RESOLUTION,
    MOCKED_RATE_CLASS,
    MOCKED_RUNNER_AGG_STATE,
    MOCKED_UPDATE_INTERVAL,
    async_get_mocked_utxos,
    node_config,
)

import pytest
from charli3_offchain_core import Node
from charli3_offchain_core.datums import DataFeed, PriceData, PriceFeed
from mocket import async_mocketize

from backend.runner import FeedUpdater


async def update(self, rate):
    """Update calls counter"""
    if rate:
        self.update_calls = 1
    else:
        self.update_calls = 0
    self.aggregate_calls = 0


async def aggregate(self):
    """aggregate calls counter"""
    self.update_calls = 1
    self.aggregate_calls = 0


MOCKED_RUNNER_OPERATE_CASES = [
    {
        "nodes_updated": 0,
        "req_nodes": 3,
        "new_rate": 445210,
        "get_paid": 1,
        "own_feed": PriceFeed(DataFeed(df_value=466087, df_last_update=1657297865999)),
        "oracle_feed": (
            PriceData.set_price_map(
                466087,
                int(datetime.timestamp(datetime.now())),
                int(datetime.timestamp(datetime.now())) + 6000,
            )
        ),
        "expected_results": {
            "update_calls": 1,
            "aggregate_calls": 0,
        },
    },
    {
        "nodes_updated": 3,
        "req_nodes": 3,
        "new_rate": 445210,
        "get_paid": 1,
        "own_feed": PriceFeed(
            DataFeed(df_value=426087, df_last_update=int(1657297865999))
        ),
        "oracle_feed": (PriceData.set_price_map(466087, 1657297865999, 1657297865999)),
        "expected_results": {
            "update_calls": 1,
            "aggregate_calls": 0,
        },
    },
]


@pytest.mark.asyncio
class TestFeedOperateClass:
    """Class to Test Runner"""

    async def test_mocked_cases(self, monkeypatch, get_chain_query):
        """Loading case for an *CASE* trigger"""

        chain_query = await get_chain_query
        for case in MOCKED_RUNNER_OPERATE_CASES:
            await self._feed_operate(case, monkeypatch, chain_query)

    async def test_initialize_feed(self, monkeypatch, get_chain_query):
        """Method to test if runner initializes with correct data"""

        chain_query = await get_chain_query
        feed_updater = await self.get_feed_updater(monkeypatch, chain_query)

        monkeypatch.setattr(feed_updater.context, "get_utxos", async_get_mocked_utxos)

        await feed_updater.initialize_feed()

        assert feed_updater.agg_datum == MOCKED_RUNNER_AGG_STATE

    @async_mocketize
    async def get_feed_updater(self, monkeypatch, chain_query):
        """Retuns feed updater for test ussage"""

        monkeypatch.setattr(Node, "update", update)
        monkeypatch.setattr(Node, "aggregate", aggregate)

        mocked_chain_query = chain_query

        mocked_node = Node(*node_config(mocked_chain_query))

        feed_updater = FeedUpdater(
            MOCKED_UPDATE_INTERVAL,
            MOCKED_PERCENT_RESOLUTION,
            MOCKED_DESTINATION_ADDRESS,
            MOCKED_COLLECTION_TRIGGER,
            mocked_node,
            MOCKED_RATE_CLASS,
            mocked_chain_query,
        )

        return feed_updater

    async def _feed_operate(self, case, monkeypatch, chain_query):
        """Method to test update - aggregate cases"""

        feed_updater = await self.get_feed_updater(monkeypatch, chain_query)

        feed_updater.agg_datum = MOCKED_RUNNER_AGG_STATE

        update_calls = case["expected_results"]["update_calls"]
        aggregate_calls = case["expected_results"]["aggregate_calls"]

        del case["expected_results"]

        await feed_updater.feed_operate(**case)  # pylint: disable = E1123

        assert feed_updater.node.update_calls == update_calls
        assert feed_updater.node.aggregate_calls == aggregate_calls
