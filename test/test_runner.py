"""Test for backend runner"""
from datetime import datetime

from test.helper.mocked_data import (
    MOCKED_CHAIN_QUERY_CONTEXT,
    MOCKED_PERCENT_RESOLUTION,
    MOCKED_RATE_CLASS,
    MOCKED_UPDATE_INTERVAL,
    MOCKED_RUNNER_AGG_STATE,
    get_mocked_init,
    async_get_mocked_utxos,
    node_config,
)

import pytest

from backend.api import ChainQuery, Node
from backend.core.datums import (
    DataFeed,
    PriceFeed,
    PriceData,
)
from backend.runner import FeedUpdater


async def update(self, rate):
    """Update calls counter"""
    if rate:
        self.update_calls = 1
    else:
        self.update_calls = 0
    self.aggregate_calls = 0
    self.update_aggregate_calls = 0


async def aggregate(self):
    """aggregate calls counter"""
    self.update_calls = 0
    self.aggregate_calls = 1
    self.update_aggregate_calls = 0


async def update_aggregate(self, rate):
    """Update-aggregate calls counter"""
    self.update_calls = 0
    self.aggregate_calls = 0
    if rate:
        self.update_aggregate_calls = 1
    else:
        self.update_aggregate_calls = 0


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
            "update_aggregate_calls": 0,
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
            "update_calls": 0,
            "aggregate_calls": 0,
            "update_aggregate_calls": 1,
        },
    },
]


@pytest.mark.asyncio
class TestFeedOperateClass:
    """Class to Test Runner"""

    async def test_mocked_cases(self, monkeypatch):
        """Loading case for an *CASE* trigger"""

        for case in MOCKED_RUNNER_OPERATE_CASES:
            await self._feed_operate(case, monkeypatch)

    async def test_initialize_feed(self, monkeypatch):
        """Method to test if runner initializes with correct data"""

        feed_updater = self.get_feed_updater(monkeypatch)

        monkeypatch.setattr(feed_updater.context, "get_utxos", async_get_mocked_utxos)

        await feed_updater.initialize_feed()

        assert feed_updater.agg_datum == MOCKED_RUNNER_AGG_STATE

    def get_feed_updater(self, monkeypatch):
        """Retuns feed updater for test ussage"""

        monkeypatch.setattr(ChainQuery, "__init__", get_mocked_init)

        monkeypatch.setattr(Node, "update", update)
        monkeypatch.setattr(Node, "aggregate", aggregate)
        monkeypatch.setattr(Node, "update_aggregate", update_aggregate)

        mocked_node = Node(*node_config(ChainQuery(*MOCKED_CHAIN_QUERY_CONTEXT)))

        feed_updater = FeedUpdater(
            MOCKED_UPDATE_INTERVAL,
            MOCKED_PERCENT_RESOLUTION,
            mocked_node,
            MOCKED_RATE_CLASS,
            ChainQuery(*MOCKED_CHAIN_QUERY_CONTEXT),
        )

        return feed_updater

    async def _feed_operate(self, case, monkeypatch):
        """Method to test update - aggregate cases"""

        feed_updater = self.get_feed_updater(monkeypatch)

        feed_updater.agg_datum = MOCKED_RUNNER_AGG_STATE

        update_calls = case["expected_results"]["update_calls"]
        aggregate_calls = case["expected_results"]["aggregate_calls"]
        update_aggregate_calls = case["expected_results"]["update_aggregate_calls"]

        del case["expected_results"]

        await feed_updater.feed_operate(**case)  # pylint: disable = E1123

        assert feed_updater.node.update_calls == update_calls
        assert feed_updater.node.aggregate_calls == aggregate_calls
        assert feed_updater.node.update_aggregate_calls == update_aggregate_calls
