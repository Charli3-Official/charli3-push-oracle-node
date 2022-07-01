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
DATUM = "d87b9fd8799fd8799fd8799f1a000b85381b00000180f77ed897ffffd8799f1b00000180f789d517ff80d87a80ffff"

@pytest.mark.asyncio
class TestChainQueryClasse():
    """Test ChainQuery Class"""

    api = ChainQuery('http://54.219.17.88:7081/')

    def register_api_uri(self, url, body):
        """SETTING UP MOCK url responses."""
        httpretty.register_uri(
            httpretty.POST,
            url,
            body=json.dumps(body),
            **{"Content-Type": "application/json"}
        )

    def _register_endpoint(self):
        self.register_api_uri(
            f"{self.api.api_url}{'utxo-with-currency'}",
            get_currency_utxos_mock
        )
        self.register_api_uri(
            f"{self.api.api_url}{'unspent-tx-out'}",
            get_datum_mock
        )
        self.register_api_uri(
            f"{self.api.api_url}{'from-hash/datum'}",
            DATUM
        )

    @async_mocketize(strict_mode=True)
    async def test_get_currency_utxos(self):
        """test currency utxos endpoint"""
        self._register_endpoint()
        data = await self.api.get_currency_utxos(ORACLE_NFT)
        data.should.equal(get_currency_utxos_mock['page']['pageItems'])

    @async_mocketize(strict_mode=True)
    async def test_get_datum(self):
        """test datum endpoint"""
        self._register_endpoint()
        data = await self.api.get_datum(ORACLE_UTXO)
        data.should.equal(get_datum_mock['_ciTxOutDatum']['Right'])

    @async_mocketize(strict_mode=True)
    async def test_get_datum_hash(self):
        """test datum-hash endpoint"""
        self._register_endpoint()
        data = await self.api.get_datum_from_hash(DATUM_HASH)
        data.should.equal(DATUM)

    @async_mocketize(strict_mode=True)
    async def test_get_oracle_datum(self):
        """test get_oracle_datum endpoint"""
        self._register_endpoint()
        data = await self.api.get_oracle_datum(ORACLE_NFT)
        data.oracle_feed.timestamp.should.equal(1655474743999)
        data.oracle_feed.value.should.equal(460000)



# mock response of get_currency_utxos
get_currency_utxos_mock = {
    "currentTip": {
        "tag": "Tip",
        "tipBlockNo": 3655250,
        "tipBlockId": "15efda321af2b87d613fd4840940c454f4619bd11b3f94e76a579c4c6e666f02",
        "tipSlot": {
            "getSlot": 61675831
        }
    },
    "page": {
        "currentPageQuery": {
            "pageQueryLastItem": None,
            "pageQuerySize": {
                "getPageSize": 50
            }
        },
        "pageItems": [
            {
                "txOutRefId": {
                    "getTxId": "4288e6fe0a20c9daf9548dae36211d78b707eea75267418e6d16ab934d304ec3"
                },
                "txOutRefIdx": 3
            }
        ],
        "nextPageQuery": None
    }
}

# mock response of get_datum
get_datum_mock = {
    "_ciTxOutValidator": {
        "Right": {
            "getValidator": ""
        }
    },
    "tag": "ScriptChainIndexTxOut",
    "_ciTxOutAddress": {
        "addressStakingCredential": None,
        "addressCredential": {
            "contents": "3567adaca6cf5156bfff96e1b88e114afde6bfa8f797fb742d628a51",
            "tag": "ScriptCredential"
        }
    },
    "_ciTxOutValue": {
        "getValue": [
            [
                {
                    "unCurrencySymbol": ""
                },
                [
                    [
                        {
                            "unTokenName": ""
                        },
                        2000000
                    ]
                ]
            ],
            [
                {
                    "unCurrencySymbol": "e106ae90da0d5d4b155cd9477a440a043715cc24eb3996a4bee4d76f"
                },
                [
                    [
                        {
                            "unTokenName": "OracleFeed"
                        },
                        1
                    ]
                ]
            ]
        ]
    },
    "_ciTxOutDatum": {
        "Right": "d87b9fd8799fd8799fd8799f1a000704e01b0000018171fbeabfffffd8799f1b000001817206e73fff80d87a80ffff"
    }
}
