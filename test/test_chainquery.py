#!/usr/bin/env python3
"""Chain query class testing."""

import json

import pytest
import sure  # pylint: disable=unused-import
from mocket import async_mocketize
from mocket.plugins.httpretty import httpretty
from backend.api.chainquery import ChainQuery

# Variables
ORACLE_NFT = (
    "24c19e34702eb1bafa2f7598570992d79b91de7d3e38790f6cfaa221", "OracleFeed")
ORACLE_UTXO = {
    "txOutRefId": {
        "getTxId": "4288e6fe0a20c9daf9548dae36211d78b707eea75267418e6d16ab934d304ec3"
    },
    "txOutRefIdx": 3
}
DATUM_HASH = "47f37db205ebdc6cbe4ff9318d26768c6b222f471b8809a521d2c2517cce9cbb"
DATUM = ("d87b9fd8799fd8799fd8799f1a000b85381b00000180f77"
         "ed897ffffd8799f1b00000180f789d517ff80d87a80ffff")

@pytest.mark.asyncio
class TestChainQueryClasse():
    """Test ChainQuery Class"""

    api = ChainQuery('http://54.177.190.73:9080/')

    def register_api_uri(self, url, body):
        """SETTING UP MOCK url responses."""
        httpretty.register_uri(
            httpretty.POST,
            url,
            body=json.dumps(body),
            **{"Content-Type": "application/json"}
        )




# mock response of get_currency_utxos
