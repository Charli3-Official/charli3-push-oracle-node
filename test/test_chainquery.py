#!/usr/bin/env python3
"""Chain query class testing."""
import json

import pytest
import sure  # pylint: disable=unused-import
from mocket import async_mocketize
from mocket.plugins.httpretty import httpretty
from backend.api.chainquery import ChainQuery


@pytest.mark.asyncio
class TestChainQueryClasse():
    """Test ChainQuery Class"""

    api = ChainQuery()
    def register_api_uri(self, url, body):
        """SETTING UP MOCK url responses."""
        httpretty.register_uri(
            httpretty.POST,
            url,
            body=json.dumps(body),
            **{"Content-Type": "application/json"}
        )

    @async_mocketize(strict_mode=True)
    async def test_get_currency_utxos(self):
        """test currency utxos endpoint"""
        nft = ("24c19e34702eb1bafa2f7598570992d79b91de7d3e38790f6cfaa221", "OracleFeed")
        self.register_api_uri(
            f"{self.api.api_url}{'utxo-with-currency'}",
            get_currency_utxos_mock
        )
        data = await self.api.get_currency_utxos(nft)
        data.should.equal(get_currency_utxos_mock['page']['pageItems'])

    @async_mocketize(strict_mode=True)
    async def test_get_datum(self):
        """test datum endpoint"""
        utxo = {
            "txOutRefId": {
                "getTxId": "02e58d8cf6c18c9eac82491cba93b8c21f04271fd329c7fb7ae27a3c7de5e26d"
            },
            "txOutRefIdx": 0
        }
        self.register_api_uri(
            f"{self.api.api_url}{'unspent-tx-out'}",
            get_datum_mock
        )
        data = await self.api.get_datum(utxo)
        data.should.equal(get_datum_mock['_ciTxOutDatum']['Right'])

    @async_mocketize(strict_mode=True)
    async def test_get_datum_hash(self):
        """test datum-hash endpoint"""
        datum_hash = "47f37db205ebdc6cbe4ff9318d26768c6b222f471b8809a521d2c2517cce9cbb"
        datum = "d87b9fd8799fd8799fd8799f1a000b85381b00000180f77ed897ffffd8799f1b00000180f789d517ff80d87a80ffff"
        self.register_api_uri(
            f"{self.api.api_url}{'from-hash/datum'}",
            datum
        )
        data = await self.api.get_datum_from_hash(datum_hash)
        data.should.equal(datum)


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
                    "getTxId": "3b4934528590c50f11f9bbee8a205fd49bca794034e433f732d47398c9253a93"
                },
                "txOutRefIdx": 6
            }
        ],
        "nextPageQuery": None
    }
}

# mock response of get_datum
get_datum_mock = {
    "_ciTxOutValidator": {
        "Left": "daacdb7f5d6a4f0a992e13d693f777e9ef1f5bd0fab5a9b1543772bb"
    },
    "tag": "ScriptChainIndexTxOut",
    "_ciTxOutAddress": {
        "addressStakingCredential": None,
        "addressCredential": {
            "contents": "daacdb7f5d6a4f0a992e13d693f777e9ef1f5bd0fab5a9b1543772bb",
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
                    "unCurrencySymbol": "24c19e34702eb1bafa2f7598570992d79b91de7d3e38790f6cfaa221"
                },
                [
                    [
                        {
                            "unTokenName": "NodeFeed"
                        },
                        1
                    ]
                ]
            ]
        ]
    },
    "_ciTxOutDatum": {
        "Right": "fc6b8e2310615801ddf54570ee3e4a7a2b0343c8b21c9a52aa40c56f503c6125"
    }
}
