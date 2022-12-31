#!/usr/bin/env python3

from backend.api import *
from .core.oracle import OracleSettings

class FeedUpdater(object):
    """Main thread for managing a node feed"""
    def __init__(self,
        update_inter: int,
        settings: OracleSettings,
        node: NodeContractApi,
        rate: CoinRate,
        chain: ChainQuery):
        pass

    def run(self):
        pass