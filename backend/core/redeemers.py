"""Redeemers for Oracle txs."""
from dataclasses import dataclass
from pycardano import PlutusData


@dataclass
class NodeUpdate(PlutusData):
    """Class for Node update redeemer"""
    CONSTR_ID = 0


@dataclass
class NodeCollect(PlutusData):
    """Class for Node collect redeemer"""
    CONSTR_ID = 1


@dataclass
class Aggregate(PlutusData):
    """Class for Aggregate redeemer"""
    CONSTR_ID = 2


@dataclass
class UpdateAndAggregate(PlutusData):
    """Class for Update and Aggregate redeemer"""
    CONSTR_ID = 3
    pub_key_hash: bytes


@dataclass
class UpgradeOracle(PlutusData):
    """Class for Oracle upgrade redeemer"""
    CONSTR_ID = 4


@dataclass
class UpdateSettings(PlutusData):
    """Class for Update settings redeemer"""
    CONSTR_ID = 5


@dataclass
class OracleClose(PlutusData):
    """Class for Oracle close redeemer"""
    CONSTR_ID = 6
