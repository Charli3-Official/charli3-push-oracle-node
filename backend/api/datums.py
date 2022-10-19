"""Datum parser classes"""

from dataclasses import dataclass
from cbor2 import loads

@dataclass
class Feed():
    """Information class for the Feed type of the oracle"""
    value: int
    timestamp: int
    initialized: bool

    @classmethod
    def from_cbor(cls, cbor):
        """Parses the information from the cbor recieved from the Datums"""
        value = None
        timestamp = None
        initialized = False
        if len(cbor) > 0 :
            feed = cbor[0].value
            value = feed[0]
            timestamp = feed[1]
            initialized = True

        return cls(value, timestamp, initialized)

    @classmethod
    def from_blockfrost(cls, data):
        """Parses the information from the blockfrost datatype"""
        value = False
        timestamp = None
        initialized = False
        if len(data) > 0 :
            feed = data[0].fields
            value = feed[0].int
            timestamp = feed[1].int
            initialized = True

        return cls(value, timestamp, initialized)

    def has_value(self):
        """Returns if the Feed has a value"""
        return self.initialized


@dataclass()
class OracleDatum():
    """Representation for Oracle Datums"""
    oracle_feed: Feed
    expiry_date: int
    whitelist: list[bytes]
    feed_enabled: bool

    @classmethod
    def from_cbor(cls, cbor):
        """Parses the cbor recieved from the chain-index for OracleDatum objects"""
        # parse cbor and get feed, expiry, whitelist, enabled.
        oracle_datum = loads(bytes.fromhex(cbor))
        oracle_feed = Feed.from_cbor(oracle_datum.value[0].value[0].value)
        expiry_date = None
        if oracle_feed.has_value():
            expiry_date = oracle_datum.value[0].value[1].value[0]
        whitelist = oracle_datum.value[0].value[2]
        feed_enabled = oracle_datum.value[0].value[3]

        return cls(oracle_feed, expiry_date, whitelist, feed_enabled)

    @classmethod
    def from_blockfrost(cls, data):
        """Parses the blockfrost datum datatype onto an oracle datum"""
        # parse cbor and get feed, expiry, whitelist, enabled.
        oracle_datum = data
        oracle_feed = Feed.from_blockfrost(
            oracle_datum.fields[0].fields[0].fields
        )
        expiry_date = None
        if oracle_feed.has_value():
            expiry_date = oracle_datum.fields[0].fields[1].fields[0].int
        whitelist = []
        for add in oracle_datum.fields[0].fields[2].list:
            whitelist.append(add.bytes)
        feed_enabled = bool(oracle_datum.fields[0].fields[3].constructor)

        return cls(oracle_feed, expiry_date, whitelist, feed_enabled)

@dataclass
class NodeDatum():
    """Representation for Node Datums"""
    node_operator: bytes
    node_feed: Feed

    @classmethod
    def from_cbor(cls, cbor):
        """Parses the cbor recieved from the chain-index for NodeDatum objects"""
        # parse cbor and get feed, node-operator.
        node_datum = loads(bytes.fromhex(cbor))
        node_operator = node_datum.value[0].value[0].value[0].hex()
        node_feed = Feed.from_cbor(node_datum.value[0].value[1].value)

        return cls(node_operator, node_feed)

    @classmethod
    def from_blockfrost(cls, data):
        """Parses the blockfrost datum datatype onto a Node Datum"""
        # parse cbor and get feed, node-operator.
        node_datum = data
        node_operator = node_datum.fields[0].fields[0].fields[0].bytes
        node_feed = Feed.from_blockfrost(
            node_datum.fields[0].fields[1].fields
        )

        return cls(node_operator, node_feed)

@dataclass
class AggStateDatum():
    """ Retrieves from blockchain feed + oracle parameters for runer """
    node_pkhs: list[bytes]
    required_nodes: int
    node_expiry: int
    aggregate_time: int
    aggregate_change: int
    node_fee: int
    mad_mult: int
    divergence: int

    @classmethod
    def from_blockfrost(cls, data):
        """ Parses blockfrost response into datums """
        agg_state = data
        node_pkhs= agg_state.fields[0].fields[0].fields[0].list
        required_nodes= agg_state.fields[0].fields[0].fields[1].int
        node_expiry= agg_state.fields[0].fields[0].fields[2].int
        aggregate_time= agg_state.fields[0].fields[0].fields[3].int
        aggregate_change= agg_state.fields[0].fields[0].fields[4].int
        node_fee= agg_state.fields[0].fields[0].fields[5].fields[0].int
        mad_mult= agg_state.fields[0].fields[0].fields[6].int
        divergence= agg_state.fields[0].fields[0].fields[7].int

        return cls(node_pkhs,required_nodes, node_expiry, aggregate_time,
            aggregate_change, node_fee, mad_mult, divergence)
