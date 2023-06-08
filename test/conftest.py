"""Pytest fixtures for tests"""
from test.helper.mocked_data import (
    MOCKED_ORACLE_ADDRESS,
    PROTOCOL_RESULT,
    GENESIS_RESULT,
    MOCKED_OGMIOS_URL,
    get_mocked_utxos,
)
import pytest
from pycardano import OgmiosChainContext, Network


from backend.api import ChainQuery


@pytest.fixture
def ogmios_context(monkeypatch):
    """Ogmios context fixture"""

    def override_request(self, method, args):
        """Override request method for OgmiosChainContext"""
        if args["query"] == "currentProtocolParameters":
            return PROTOCOL_RESULT
        if args["query"] == "genesisConfig":
            return GENESIS_RESULT
        if "chainTip" in args["query"]:
            return {"slot": 100000000}
        else:
            raise NotImplementedError(f"Method {method} not implemented in mock")

    monkeypatch.setattr(OgmiosChainContext, "_request", override_request)
    context = OgmiosChainContext(MOCKED_OGMIOS_URL, Network.TESTNET)
    return context


@pytest.fixture
async def get_chain_query(monkeypatch, ogmios_context):
    """ChainQuery fixture with mocked methods"""
    monkeypatch.setattr(ChainQuery, "get_utxos", get_mocked_utxos)
    chain_query_context = (
        None,
        ogmios_context,
        MOCKED_ORACLE_ADDRESS,
    )
    return ChainQuery(*chain_query_context)
