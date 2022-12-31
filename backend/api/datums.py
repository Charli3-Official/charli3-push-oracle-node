#!/usr/bin/env python3

class OracleDatum(object):
    """Parses the cbor recieved from the chain-index for OracleDatum objects"""
    def __init__(self, cbor):
        # TODO: parse cbor and get feed, expiry, whitelist, enabled.
        pass

class NodeDatum(object):
    """Parses the cbor recieved from the chain-index for NodeDatum objects"""
    def __init__(self, cbor):
        # TODO: parse cbor and get feed, node-operator.
        pass

class Feed(object):
    """Information class for the Feed type of the oracle"""
    def __init__(self, cbor):
        # TODO: parse cbor and get value, timestamp.
        pass