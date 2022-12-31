#!/usr/bin/env python3

class Oracle(object):
    def __init__(self, oracle_curr, fee_asset, oracle_owner):
        self.oracle_curr = oracle_curr
        self.fee_asset = fee_asset
        self.oracle_owner = oracle_owner

    def to_json(self):
        if (hasattr(self, "_json")):
            return self._json
        json = None
        # TODO: build json for the oracle.
        self._json = json
        return self._json

class OracleSettings(object):
    def __init__(self, node_pkhs, required_nodes, node_expiry, aggregate_time,
                 aggregate_change, node_fee, mad_mult, divergence):
        self.node_pkhs = node_pkhs
        self.required_nodes = required_nodes
        self.node_expiry = node_expiry
        self.aggregate_time = aggregate_time
        self.aggregate_change = aggregate_change
        self.node_fee = node_fee
        self.mad_mult = mad_mult
        self.divergence = divergence