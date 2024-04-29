"""Chain query class testing."""
from test.helper.mocked_data import MOCKED_ORACLE_ADDRESS, MOCKED_UTXOS_RESPONSE

import pytest
from mocket import async_mocketize


@pytest.mark.asyncio
class TestChainQueryClass:
    """Test ChainQuery Class"""

    @async_mocketize(strict_mode=True)
    async def test_get_utxos(self, get_chain_query):
        """test_get_utxos"""
        chainquery = await get_chain_query
        utxos = await chainquery.get_utxos()
        assert utxos == MOCKED_UTXOS_RESPONSE

    @async_mocketize(strict_mode=True)
    async def test_find_collateral(self, get_chain_query):
        """test_find_collateral"""
        chainquery = await get_chain_query
        assert MOCKED_UTXOS_RESPONSE[9] == await chainquery.find_collateral(
            MOCKED_ORACLE_ADDRESS, 9000000
        )
