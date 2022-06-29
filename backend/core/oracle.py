#!/usr/bin/env python3
"""This module contains the oracle information classes"""
import json
from dataclasses import dataclass
from math import ceil

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

    def get_oracle_feed_nft(self):
        """Get the OracleFeed NFT"""
        return (self.oracle_curr,"OracleFeed")

    def get_aggstate_nft(self):
        """Get the aggstate nft"""
        return (self.oracle_curr,"AggState")

    def get_node_feed_nft(self):
        """Get the NodeFeed token"""
        return (self.oracle_curr,"NodeFeed")

    def to_dict(self):
        """Generate and cache a dict for the pab"""
        if not hasattr(self,"_dict"):
            # pylint: disable=attribute-defined-outside-init
            self._dict = {
                "feeToken": self._asset_class(*self.fee_asset),
                "aggStateNFT": self._asset_class(*self.get_aggstate_nft()),
                "oracleNFT": self._asset_class(*self.get_oracle_feed_nft()),
                "nodeToken": self._asset_class(*self.get_node_feed_nft()),
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
    percent_resolution: int

    def required_nodes_num(self):
        """Number of nodes required"""
        n_nodes = len(self.node_pkhs)
        return ceil(self.required_nodes*n_nodes/self.percent_resolution)
