"""Datum testing module"""

import json

from backend.core import Oracle

class TestOracle():
    """Testig cases for the Oracle class"""

    def test_to_json(self):
        """Testing the to_json method"""
        pkh = "PubKeyHash"
        ocurr = "OralcleCurrency"
        oaddress= "addr_test1wzk0kq5llrne68rusc2zj480xgj3fxsny2kmupha53vegdgz6rzg6"
        charli3 = ("Charli3Currency", "CHARLI3")
        oracle = Oracle(pkh, ocurr, oaddress, charli3)

        valid_json = {
            "feeToken": {
                "unAssetClass": [{
                    "unCurrencySymbol": charli3[0]
                },
                {
                    "unTokenName": charli3[1]
                }]
            },
            "aggStateNFT": {
                "unAssetClass": [{
                    "unCurrencySymbol": ocurr
                },
                {
                    "unTokenName": "AggState"
                }]
            },
            "oracleNFT": {
                "unAssetClass": [{
                    "unCurrencySymbol": ocurr
                },
                {
                    "unTokenName": "OracleFeed"
                }]
            },
            "nodeToken": {
                "unAssetClass": [{
                    "unCurrencySymbol": ocurr
                },
                {
                    "unTokenName": "NodeFeed"
                }]
            },
            "oracleCreator": {
                "unPaymentPubKeyHash": {
                    "getPubKeyHash": pkh
                }
            }
        }
        assert json.dumps(valid_json) == oracle.to_json()
