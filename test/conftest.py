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
from pycardano import Network
from pycardano.backend.ogmios_v6 import KupoOgmiosV6ChainContext, OgmiosClient


@pytest.fixture
def ogmios_context(monkeypatch):
    """Ogmios context fixture"""

    def mock_query_protocol_parameters_execute():
        """Mock method to return protocol parameters"""
        return PROTOCOL_RESULT

    def mock_query_genesis_configuration_execute():
        """Mock method to return genesis parameters"""
        return GENESIS_RESULT

    def mock_query_network_tip_execute():
        """Mock method to return chain tip"""
        return {"slot": 100000000}

    def mock_query_utxo_execute(self, addresses):
        """Mock method to return UTxOs for given addresses"""
        return get_mocked_utxos(addresses[0]), None

    _, ws_string = MOCKED_OGMIOS_URL.split("ws://")
    ws_url, port = ws_string.split(":")

    context = KupoOgmiosV6ChainContext(
        host=ws_url,
        port=int(port),
        secure=False,
        refetch_chain_tip_interval=None,
        network=Network.TESTNET,
        kupo_url=MOCKED_KUPO_URL,
    )

    monkeypatch.setattr(
        type(context),
        "genesis_param",
        property(lambda self: mock_query_genesis_configuration_execute()),
    )
    monkeypatch.setattr(
        type(context),
        "protocol_param",
        property(lambda self: mock_query_protocol_parameters_execute()),
    )
    monkeypatch.setattr(
        type(context),
        "last_block_slot",
        property(lambda self: mock_query_network_tip_execute()["slot"]),
    )

    monkeypatch.setattr(
        type(context),
        "utxos",
        lambda self, addresses: mock_query_utxo_execute(self, addresses),
    )

    return context


@pytest.fixture
async def get_chain_query(monkeypatch, ogmios_context):
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
        kupo_ogmios_context=ogmios_context,
        oracle_address=MOCKED_ORACLE_ADDRESS,
    )
