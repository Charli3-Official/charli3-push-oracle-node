"""Test for backend runner"""
from test.helper import (
    MOCKED_BLOCKFROST_API_CALL,
    MOCKED_CHAIN_QUERY_CONTEXT,
    async_get_mocked_utxos,
    get_mocked_init,
    node_config,
    register_api_uri,
)


from mocket import async_mocketize
import pytest

from backend.api import Node, ChainQuery
from backend.core.datums import DataFeed, PriceFeed


@pytest.mark.asyncio
class TestNodeClass:
    """Class to Test Runner"""

    async def test_get_node_own_utxos(self, monkeypatch):
        """Loading case for an *CASE* trigger"""

        register_api_uri(
            MOCKED_BLOCKFROST_API_CALL["api_url"],
            *MOCKED_BLOCKFROST_API_CALL["api_call"]["v0_epochs_latest"],
        )

        node = await self.get_node(monkeypatch)

        utxos = await node.context.get_utxos()

        node_own_utxo = node.get_node_own_utxo(utxos)

        assert utxos[6] == node_own_utxo

    async def test_filter_utxos_by_asset(self, monkeypatch):
        """Loading case for an *CASE* trigger"""

        register_api_uri(
            MOCKED_BLOCKFROST_API_CALL["api_url"],
            *MOCKED_BLOCKFROST_API_CALL["api_call"]["v0_epochs_latest"],
        )

        node = await self.get_node(monkeypatch)

        utxos = await node.context.get_utxos()

        # Filter AGG_STATE_NFT
        aggstate_nft_utxo = node.filter_utxos_by_asset(utxos, node.aggstate_nft)[0]
        assert utxos[4] == aggstate_nft_utxo

        # Filter ORACLE NFT
        oracle_nft_utxo = node.filter_utxos_by_asset(utxos, node.oracle_nft)[0]
        assert utxos[5] == oracle_nft_utxo

        nodes_nft_utxo = node.filter_utxos_by_asset(utxos, node.node_nft)

        assert [utxos[0], utxos[6]] == nodes_nft_utxo

    async def test_update_own_node_utxo(self, monkeypatch):
        """Loading case for an *CASE* trigger"""

        register_api_uri(
            MOCKED_BLOCKFROST_API_CALL["api_url"],
            *MOCKED_BLOCKFROST_API_CALL["api_call"]["v0_epochs_latest"],
        )

        node = await self.get_node(monkeypatch)
        utxos = await node.context.get_utxos()

        node_own_utxo = node.get_node_own_utxo(utxos)

        new_node_feed = PriceFeed(DataFeed(8888888, 12312312312312))
        node_own_utxo.output.datum.node_state.node_feed = new_node_feed

        updated_nodes_utxos = node.filter_utxos_by_asset(utxos, node.node_nft)
        updated_node = [
            utxo
            for utxo in updated_nodes_utxos
            if utxo.output.datum.node_state.node_operator == node.node_info
        ]

        assert node_own_utxo == updated_node[0]

    @async_mocketize
    async def get_node(self, monkeypatch):
        """Retuns node class test ussage"""
        monkeypatch.setattr(ChainQuery, "__init__", get_mocked_init)

        mocked_node = Node(*node_config(ChainQuery(*MOCKED_CHAIN_QUERY_CONTEXT)))

        monkeypatch.setattr(mocked_node.context, "get_utxos", async_get_mocked_utxos)

        return mocked_node
