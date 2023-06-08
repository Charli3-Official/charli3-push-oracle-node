"""Test for backend runner"""
from test.helper import (
    MOCKED_BLOCKFROST_API_CALL,
    async_get_mocked_utxos,
    node_config,
    register_api_uri,
)


from mocket import async_mocketize
import pytest

from backend.api import Node
from backend.core.datums import DataFeed, PriceFeed


@pytest.mark.asyncio
class TestNodeClass:
    """Class to Test Runner"""

    async def test_get_node_own_utxos(self, monkeypatch, get_chain_query):
        """Loading case for an *CASE* trigger"""

        register_api_uri(
            MOCKED_BLOCKFROST_API_CALL["api_url"],
            *MOCKED_BLOCKFROST_API_CALL["api_call"]["v0_epochs_latest"],
        )

        node = await self.get_node(monkeypatch, get_chain_query)

        utxos = await node.chain_query.get_utxos()

        node_own_utxo = node.get_node_own_utxo(utxos)

        assert utxos[1] == node_own_utxo

    async def test_filter_utxos_by_asset(self, monkeypatch, get_chain_query):
        """Loading case for an *CASE* trigger"""

        register_api_uri(
            MOCKED_BLOCKFROST_API_CALL["api_url"],
            *MOCKED_BLOCKFROST_API_CALL["api_call"]["v0_epochs_latest"],
        )

        node = await self.get_node(monkeypatch, get_chain_query)

        utxos = await node.chain_query.get_utxos()

        # Filter AGG_STATE_NFT
        aggstate_nft_utxo = node.filter_utxos_by_asset(utxos, node.aggstate_nft)[0]
        assert utxos[6] == aggstate_nft_utxo

        # Filter ORACLE NFT
        oracle_nft_utxo = node.filter_utxos_by_asset(utxos, node.oracle_nft)[0]
        assert utxos[7] == oracle_nft_utxo

    async def test_update_own_node_utxo(self, monkeypatch, get_chain_query):
        """Loading case for an *CASE* trigger"""

        register_api_uri(
            MOCKED_BLOCKFROST_API_CALL["api_url"],
            *MOCKED_BLOCKFROST_API_CALL["api_call"]["v0_epochs_latest"],
        )

        node = await self.get_node(monkeypatch, get_chain_query)
        utxos = await node.chain_query.get_utxos()

        node_own_utxo = node.get_node_own_utxo(utxos)

        new_node_feed = PriceFeed(DataFeed(8888888, 12312312312312))
        node_own_utxo.output.datum.node_state.ns_feed = new_node_feed

        updated_nodes_utxos = node.filter_utxos_by_asset(utxos, node.node_nft)

        updated_node = next(
            utxo
            for utxo in updated_nodes_utxos
            if utxo.output.datum.node_state.ns_operator == node.node_operator
        )

        assert node_own_utxo == updated_node

    @async_mocketize
    async def get_node(self, monkeypatch, get_chain_query):
        """Retuns node class test ussage"""
        mocked_chain_query = await get_chain_query

        mocked_node = Node(*node_config(mocked_chain_query))

        monkeypatch.setattr(
            mocked_node.chain_query, "get_utxos", async_get_mocked_utxos
        )

        return mocked_node
