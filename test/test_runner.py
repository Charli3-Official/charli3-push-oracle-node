"""Test for backend runner"""

import pytest

from backend.api import NodeContractApi, chainQueryTypes, apiTypes
from backend.api.datums import Feed
from backend.core.oracle import Oracle, OracleSettings
from backend.runner import FeedUpdater

# Mocked variables
MOCK_UPDATE_INTERVAL = 600

# Mocked class
class NodeMock(NodeContractApi):
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

MOCK_ORACLE = Oracle(
    'ef097309136a1242669c29bf772b32efad68af0405f406e92a2e1ac0',
    'de031116866f1688d288b8eb42d1c321c0a2ecaf4acb05bbf7757c02',
    ('716e6a0dc6ade9c74eae49bfb3f006e809a131d9e5f201f631f8b7d4', 'CHARLI3')
)
MOCK_NODEMOCK = NodeMock(
    MOCK_ORACLE,
    **{
        'pkh': '3a1314fa60a312d41eaf203378a6a92b5fca5c6649580e0c3e4fa707',
        'wallet_id': '71517afc9a4d6dd79294ff6be77dd6a6a3c70d95',
        'api_url': 'http://localhost:9080/api'
    }
)
MOCK_ORACLE_SETTINGS = OracleSettings(**{
    'node_pkhs': [
        'node1',
        'node2',
        'node3',
        'node4'
    ],
    'required_nodes': 3500,
    'node_expiry': 300000,
    'aggregate_time': 720000,
    'aggregate_change': 500,
    'mad_mult': 20000,
    'divergence': 1500,
    'percent_resolution': 10000
})

MOCK_RATE_CLASS =  apiTypes['binance'](** {'symbol': 'ADAUSDT'})

MOCK_CHAIN_QUERY = chainQueryTypes['blockfrost'](**{
    'api_url': 'https://cardano-testnet.blockfrost.io/api',
    'token': 'tokenblockfrost'
})

#@pytest.fixture
MOCKED_RUNNER_CASES = {
        'nodes_updated': 0,
        'req_nodes': 0,
        'new_rate': 465210,
        'own_feed': Feed(
                    value=466087,
                    timestamp=1657297865999,
                    initialized=True
                ),
        'expected_results':{
            'update_calls':1,
            'aggregate_calls':0,
            'update_aggregate_calls':0
            }
        }

@pytest.mark.asyncio
class TestFeedUpdaterClass():
    """Class to Test Runner"""

    async def test_feed_operate(self):
        """Method to test update - aggregate cases"""

        feed_updater = FeedUpdater(
            MOCK_UPDATE_INTERVAL,
            MOCK_ORACLE_SETTINGS,
            MOCK_NODEMOCK,
            MOCK_RATE_CLASS,
            MOCK_CHAIN_QUERY
            )

        update_calls = MOCKED_RUNNER_CASES['expected_results']['update_calls']
        aggregate_calls = MOCKED_RUNNER_CASES['expected_results']['aggregate_calls']
        update_aggregate_calls = MOCKED_RUNNER_CASES['expected_results']['update_aggregate_calls']

        del MOCKED_RUNNER_CASES['expected_results']

        await feed_updater.feed_operate(**MOCKED_RUNNER_CASES) # pylint: disable = E1123

        assert feed_updater.node.update_calls == update_calls
        assert feed_updater.node.aggregate_calls == aggregate_calls
        assert feed_updater.node.update_aggregate_calls == update_aggregate_calls
