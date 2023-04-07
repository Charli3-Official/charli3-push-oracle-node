"""Chain query class testing."""
import json

from test.helper.mocked_data import (
    MOCKED_ORACLE_ADDRESS,
    MOCKED_BLOCKFROST_API_CALL,
    MOCKED_CHAIN_QUERY_CONTEXT,
    MOCKED_UTXOS_RESPONSE,
    get_mocked_utxos,
    register_api_uri,
)

from mocket import async_mocketize
from mocket.plugins.httpretty import httpretty
import pytest

from backend.api import ChainQuery


@pytest.mark.asyncio
class TestChainQueryClass:
    """Test ChainQuery Class"""

    def register_api_uri(self, url, body):
        """Helper method to mock http endpoints"""
        httpretty.register_uri(
            httpretty.GET,
            url,
            body=json.dumps(body),
            **{
                "Content-Type": "application/json",
                "project_id": MOCKED_CHAIN_QUERY_CONTEXT[0],
            },
        )

    @async_mocketize(strict_mode=True)
    async def test_get_utxos(self, monkeypatch):
        """test_get_utxos"""

        chainquery = await self.get_chain_query(monkeypatch)

        utxos = await chainquery.get_utxos()

        assert utxos == MOCKED_UTXOS_RESPONSE

    @async_mocketize(strict_mode=True)
    async def test_find_collateral(self, monkeypatch):
        """test_get_utxos"""

        chainquery = await self.get_chain_query(monkeypatch)

        assert MOCKED_UTXOS_RESPONSE[3] == await chainquery.find_collateral(
            MOCKED_ORACLE_ADDRESS
        )

    @async_mocketize()
    async def get_chain_query(self, monkeypatch):
        """Runner 1st api call: blockchain context"""
        register_api_uri(
            MOCKED_BLOCKFROST_API_CALL["api_url"],
            **MOCKED_BLOCKFROST_API_CALL["api_call"]["v0_epochs_latest"],
        )

        monkeypatch.setattr(ChainQuery, "get_utxos", get_mocked_utxos)
        return ChainQuery(*MOCKED_CHAIN_QUERY_CONTEXT)
