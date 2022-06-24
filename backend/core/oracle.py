#!/usr/bin/env python3
"""This module contains the oracle information classes"""
import json
from dataclasses import dataclass

@dataclass
class Oracle:
    """Oracle data class"""
    oracle_owner: str
    oracle_curr: str
    fee_asset: tuple[str, str]

    def to_json(self):
        """Generate and cache a json for the pab"""
        if not hasattr(self, "_json"):
            # pylint: disable=attribute-defined-outside-init
            self._json = json.dumps(self.to_dict())

        return self._json

    def to_dict(self):
        """Generate and cache a dict for the pab"""
        if not hasattr(self,"_dict"):
            # pylint: disable=attribute-defined-outside-init
            self._dict = {
                "feeToken": self._asset_class(
                    self.fee_asset[0],
                    self.fee_asset[1]),
                "aggStateNFT": self._asset_class(
                    self.oracle_curr,
                    "AggStateNFT"),
                "oracleNFT": self._asset_class(
                    self.oracle_curr,
                    "OracleNFT"),
                "nodeToken": self._asset_class(
                    self.oracle_curr,
                    "NodeFeed"),
                "oracleCreator": {
                    "unPaymentPubKeyHash": {
                        "getPubKeyHash": self.oracle_owner
                    }
                }
            }
        return self._dict

    @staticmethod
    def _asset_class(currency, token_name):
        data = {
            "unAssetClass": [
                {
                    "unCurrencySymbol": currency
                },
                {
                    "unTokenName": token_name
                }
            ]
        }
        return data

@dataclass
class OracleSettings:
    """Data class to store OracleSettings"""
    node_pkhs: list[str]
    required_nodes: int
    node_expiry: int
    aggregate_time: int
    aggregate_change: float
    mad_mult: int
    divergence: int
