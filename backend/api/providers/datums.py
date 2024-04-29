"""Datums implementation"""
from dataclasses import dataclass
from pycardano import PlutusData


@dataclass
class VyFiBarFees(PlutusData):
    """Represents VyFi Bar Fees values"""

    CONSTR_ID = 0
    token_a_fees: int
    token_b_fees: int
    liquidity_pool: int
