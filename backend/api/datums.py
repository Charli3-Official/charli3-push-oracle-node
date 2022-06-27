"""Datum parser classes"""

from dataclasses import dataclass
from cbor2 import loads


@dataclass(init=False)
class OracleDatum():
    """Parses the cbor recieved from the chain-index for OracleDatum objects"""

    def __init__(self, cbor):
        # parse cbor and get feed, expiry, whitelist, enabled.
        self.oracle_datum = loads(bytes.fromhex(cbor))
        if len(self.oracle_datum.value[0].value[0].value) > 0:
            self.oracle_feed = Feed(
                self.oracle_datum.value[0].value[0].value[0].value
            )
            self.expiry_date = self.oracle_datum.value[0].value[1].value[0]
            self.whitelist = self.oracle_datum.value[0].value[2]
            self.feed_enabled = self.oracle_datum.value[0].value[3]


@dataclass
class NodeDatum():
    """Parses the cbor recieved from the chain-index for NodeDatum objects"""

    def __init__(self, cbor):
        # parse cbor and get feed, node-operator.
        self.node_datum = loads(bytes.fromhex(cbor))
        self.node_operator = self.node_datum.value[0].value[0].value[0].hex()
        if len(self.node_datum.value[0].value[1].value) > 0 :
            self.node_feed = Feed(
                self.node_datum.value[0].value[1].value[0].value)
        else:
            self.node_feed = None


@dataclass
class Feed():
    """Information class for the Feed type of the oracle"""

    def __init__(self, feed):
        # parse cbor and get value, timestamp.
        self.value = feed[0]
        self.timestamp = feed[1]
