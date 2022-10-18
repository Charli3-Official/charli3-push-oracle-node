#!/usr/bin/env python3
"""This module contains the oracle information classes"""
import json
from dataclasses import dataclass
from math import ceil
from backend.api.datums import AggStateDatum


@dataclass
class Oracle:
    """Oracle data class"""
    oracle_owner: str
    oracle_curr: str
    oracle_address: str
    fee_asset: tuple[str, str]

    def to_json(self):
        """Generate and cache a json for the pab"""
        if not hasattr(self, "_json"):
            # pylint: disable=attribute-defined-outside-init
            self._json = json.dumps(self.to_dict())

        return self._json

    def get_oracle_feed_nft(self):
        """Get the OracleFeed NFT"""
        return (self.oracle_curr, "OracleFeed")

    def get_aggstate_nft(self):
        """Get the aggstate nft"""
        return (self.oracle_curr, "AggState")

    def get_node_feed_nft(self):
        """Get the NodeFeed token"""
        return (self.oracle_curr, "NodeFeed")

    def get_fee_asset(self):
        """Get Fee (c3) asset token"""
        return self.fee_asset

    def get_oracle_address(self):
        """Get Oracle Address"""
        return self.oracle_address

    def to_dict(self):
        """Generate and cache a dict for the pab"""
        if not hasattr(self, "_dict"):
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
    percent_resolution: int
    agg_state_datum: AggStateDatum
    agg_state_datum_hash: str

    def required_nodes_num(self):
        """Number of nodes required"""
        n_nodes = len(self.agg_state_datum.node_pkhs)
        return ceil(self.agg_state_datum.required_nodes*n_nodes/self.percent_resolution)
