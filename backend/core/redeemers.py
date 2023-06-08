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

    CONSTR_ID = 3
