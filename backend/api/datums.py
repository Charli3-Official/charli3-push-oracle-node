#!/usr/bin/env python3
from cbor2 import loads

class OracleDatum(object):
    """Parses the cbor recieved from the chain-index for OracleDatum objects"""
    def __init__(self, cbor):
        # parse cbor and get feed, expiry, whitelist, enabled.
        self.oracleDatum    = loads(bytes.fromhex(cbor))
        self.oracleFeed     = Feed(self.oracleDatum.value[0].value[0].value[0].value)
        self.expiryDate     = self.oracleDatum.value[0].value[1].value[0]
        self.whitelist      = self.oracleDatum.value[0].value[2]
        self.feedEnabled    = self.oracleDatum.value[0].value[3]
        # print(self.oracleDatum, '\n')
        # print(self.oracleFeed.value)
        # print(self.expiryDate)

class NodeDatum(object):
    """Parses the cbor recieved from the chain-index for NodeDatum objects"""
    def __init__(self, cbor):
        # parse cbor and get feed, node-operator.
        self.nodeDatum      = loads(bytes.fromhex(cbor))
        self.nodeOperator   = self.nodeDatum.value[0].value[0].value[0].hex()
        self.nodeFeed       = Feed(self.nodeDatum.value[0].value[1].value[0].value)
        # print(self.nodeOperator, '\n',self.nodeFeed.value)

class Feed(object):
    """Information class for the Feed type of the oracle"""
    def __init__(self, feed):
        # parse cbor and get value, timestamp.
        self.value      = feed[0]
        self.timestamp  = feed[1]
        # print('\n',self.value,'\n',self.timestamp)