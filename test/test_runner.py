"""Test for backend runner"""
import pytest

from backend.api import AggregatedCoinRate, Node, ChainQuery
from backend.core.datums import PriceFeed, PriceData, DataFeed
from backend.runner import FeedUpdater

# Mocked variables
MOCK_UPDATE_INTERVAL = 600

# Mocked class
class NodeMock(Node):
    """Node Mocked for Runner Testing"""
    update_calls = 0
    aggregate_calls = 0
    update_aggregate_calls = 0

    async def update(self,rate):
        #super().update(new_rate)
        self.update_calls += 1

    async def aggregate(self):
        #super().aggregate(new_rate)
        self.aggregate_calls += 1

    async def update_aggregate(self,rate):
        #super().update_aggregate()
        self.update_aggregate_calls += 1

# MOCK_NODEMOCK = {
#     'pkh': '3a1314fa60a312d41eaf203378a6a92b5fca5c6649580e0c3e4fa707',
#     'wallet_id': '71517afc9a4d6dd79294ff6be77dd6a6a3c70d95',
#     'api_url': 'http://localhost:9080/api'
# }

# MOCK_RATE_CLASS =  AggregatedCoinRate()
# MOCK_RATE_CLASS.add_data_provider('generic','kraken', {"symbol": "ADAUSD", "api_url": "https://api.kraken.com", "path": "/0/public/Ticker?pair=", "json_path": ["result", "ADAUSD", "o"], "key": {}})
# MOCK_RATE_CLASS.add_data_provider('generic','kucoin', {"symbol": "BTC-USDT", "api_url": "https://openapi-sandbox.kucoin.com", "path": "/api/v1/market/orderbook/level1?symbol=", "json_path": ["data", "price"], "key": {}})

# MOCK_CHAIN_QUERY = ChainQuery(
#     project_id='tokenblockfrost',
#     base_url= 'https://cardano-testnet.blockfrost.io/api',
#     network= 'testnet',
#     oracle_address='oracle_address',
# )

# #@pytest.fixture
# MOCKED_RUNNER_CASES = [
#     {
#         'nodes_updated': 0,
#         'req_nodes': 3,
#         'new_rate': 465210,
#         'feed_balance':1,
#         'node_fee':0,
#         'own_feed': PriceFeed(df=DataFeed(df_value=466087, df_last_update=1657297865999 )),
#         'oracle_feed': PriceData.set_price_map(466087,1657297865999,1657298865999),
#         'expected_results':{
#             'update_calls':1,
#             'aggregate_calls':0,
#             'update_aggregate_calls':0
#         }
#     },
#     {
#         'nodes_updated': 2,
#         'req_nodes': 3,
#         'new_rate': 465210,
#         'feed_balance':1,
#         'node_fee':0,
#         'own_feed': PriceFeed(df=DataFeed(df_value=466087, df_last_update=1657297865999 )),
#         'oracle_feed': PriceData.set_price_map(466087,1657297865999,1657298865999),
#         'expected_results':{
#             'update_calls':0,
#             'aggregate_calls':0,
#             'update_aggregate_calls':1
#         }
#     }
# ]

# @pytest.mark.asyncio
# class TestFeedUpdaterClass():
#     """Class to Test Runner"""

#     async def test_without_updates(self):
#         """Oracle without any updated nodes"""
#         await self._feed_operate(MOCKED_RUNNER_CASES[0])

#     async def test_update_aggregate(self):
#         """Oracle for an update aggregate trigger"""
#         await self._feed_operate(MOCKED_RUNNER_CASES[1])

#     async def _feed_operate(self, case):
#         """Method to test update - aggregate cases"""

#         feed_updater = FeedUpdater(
#             MOCK_UPDATE_INTERVAL,
#             10000,
#             MOCK_NODEMOCK,
#             MOCK_RATE_CLASS,
#             MOCK_CHAIN_QUERY
#             )

#         update_calls = case['expected_results']['update_calls']
#         aggregate_calls = case['expected_results']['aggregate_calls']
#         update_aggregate_calls = case['expected_results']['update_aggregate_calls']

#         del case['expected_results']



#         await feed_updater.feed_operate(**case) # pylint: disable = E1123

#         assert feed_updater.node.update_calls == update_calls
#         assert feed_updater.node.aggregate_calls == aggregate_calls
#         assert feed_updater.node.update_aggregate_calls == update_aggregate_calls
