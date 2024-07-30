"""Pytest fixtures for tests"""

import time
from test.helper.mocked_data import (
    GENESIS_RESULT,
    MOCKED_KUPO_URL,
    MOCKED_OGMIOS_URL,
    MOCKED_ORACLE_ADDRESS,
    PROTOCOL_RESULT,
    get_mocked_utxos,
)

import pytest
from charli3_offchain_core import ChainQuery
from charli3_offchain_core.backend.kupo import KupoContext
from pycardano import Network, OgmiosChainContext


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
        raise NotImplementedError(f"Method {method} not implemented in mock")

    monkeypatch.setattr(OgmiosChainContext, "_request", override_request)
    context = OgmiosChainContext(MOCKED_OGMIOS_URL, Network.TESTNET)
    return context


@pytest.fixture
def kupo_context():
    """Kupo context fixture"""
    context = KupoContext(MOCKED_KUPO_URL)
    return context


@pytest.fixture
async def get_chain_query(monkeypatch, ogmios_context, kupo_context):
    """ChainQuery fixture with mocked methods"""

    async def get_empty_metadata(self, tx_id, slot):
        return None

    def get_current_posix_chain_time_ms(self) -> int:
        return round(time.time_ns() * 1e-6)

    monkeypatch.setattr(ChainQuery, "get_utxos", get_mocked_utxos)
    monkeypatch.setattr(ChainQuery, "get_metadata_cbor", get_empty_metadata)
    monkeypatch.setattr(
        ChainQuery, "get_current_posix_chain_time_ms", get_current_posix_chain_time_ms
    )
    return ChainQuery(
        blockfrost_context=None,
        ogmios_context=ogmios_context,
        oracle_address=MOCKED_ORACLE_ADDRESS,
        kupo_context=kupo_context,
    )
