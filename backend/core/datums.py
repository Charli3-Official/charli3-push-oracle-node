"""Datums implementation"""
from dataclasses import dataclass
from math import ceil
from typing import Union, Optional
from pycardano import PlutusData
from pycardano.serialization import IndefiniteList


@dataclass
class NodeInfo(PlutusData):
    """NodeInfo Datum"""
    CONSTR_ID = 0
    node_operator: bytes


@dataclass
class DataFeed(PlutusData):
    """DataFeed Datum"""
    CONSTR_ID = 0
    df_value: int
    df_last_update: int


@dataclass
class PriceFeed(PlutusData):
    """PriceFeed Datum"""
    CONSTR_ID = 0
    df: DataFeed


@dataclass
class Nothing(PlutusData):
    """Nothing Datum"""
    CONSTR_ID = 1


## Indigo format
@dataclass
class Price(PlutusData):
    """Price Datum"""
    CONSTR_ID = 0
    value: int


@dataclass
class PriceData(PlutusData):
    """represents cip oracle datum PriceMap(Tag +2)"""

    CONSTR_ID = 2
    price_map: dict

    def get_price(self) -> int:
        """get price from price map"""
        return self.price_map[0]

    def get_timestamp(self) -> int:
        """get timestamp of the feed"""
        return self.price_map[1]

    def get_expiry(self) -> int:
        """get expiry of the feed"""
        return self.price_map[2]

    @classmethod
    def set_price_map(cls, price: int, timestamp: int, expiry: int):
        """set price_map"""
        price_map = {0: price, 1: timestamp, 2: expiry}
        return cls(price_map)


@dataclass
class NodeState(PlutusData):
    """represents Node State of Node Datum"""

    CONSTR_ID = 0
    node_operator: NodeInfo
    node_feed: Union[PriceFeed, Nothing]


@dataclass
class NodeDatum(PlutusData):
    """represents Node Datum"""

    CONSTR_ID = 1
    node_state: NodeState


@dataclass
class OracleDatum(PlutusData):
    """OracleFeed Datum"""
    CONSTR_ID = 0
    price_data: Optional[PriceData] = None


@dataclass
class NodeFee(PlutusData):
    """NodeFee Datum"""
    CONSTR_ID = 0
    get_node_fee: int


@dataclass
class OracleSettings(PlutusData):
    """OracleSettings Datum"""
    CONSTR_ID = 0
    os_node_list: IndefiniteList
    os_updated_nodes: int
    os_updated_node_time: int
    os_aggregate_time: int
    os_aggregate_change: int
    os_node_fee_price: NodeFee
    os_mad_multiplier: int
    os_divergence: int

    def required_nodes_num(self, percent_resolution: int = 10000) -> int:
        """Number of nodes required"""
        n_nodes = len(self.os_node_list)
        return ceil(self.os_updated_nodes * n_nodes / percent_resolution)


@dataclass
class AggState(PlutusData):
    """AggState Datum"""
    CONSTR_ID = 0
    ag_settings: OracleSettings


@dataclass
class AggDatum(PlutusData):
    """Agg Datum"""
    CONSTR_ID = 2
    aggstate: AggState


@dataclass
class InitialOracleDatum(PlutusData):
    """Initial Oracle Datum"""
    CONSTR_ID = 0
