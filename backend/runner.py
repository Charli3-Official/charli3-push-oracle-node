"""Main updater class"""

from backend.api import NodeContractApi, CoinRate, ChainQuery
from .core.oracle import OracleSettings

class FeedUpdater():
    """Main thread for managing a node feed"""
    def __init__(self,
                 update_inter: int,
                 settings: OracleSettings,
                 node: NodeContractApi,
                 rate: CoinRate,
                 chain: ChainQuery):
        pass

    def run(self):
        """Checks and if necesary updates and/or aggregates the contract"""
