"""Main updater class"""
import asyncio
import time

from backend.api import NodeContractApi, CoinRate, ChainQuery
from backend.api.coinrate import BinanceApi
from .core.oracle import OracleSettings


class FeedUpdater():
    """Main thread for managing a node feed"""

    def __init__(self,
                 #  update_inter: int,
                 #  oracle_settings: OracleSettings,
                 #  node: NodeContractApi,
                 # rate: CoinRate,
                 #  chain: ChainQuery,
                 #  node_nft: tuple[str, str],
                 #  oracle_nft: tuple[str, str]
                 ):
        # self.update_inter = update_inter
        # self.oracle_settings = oracle_settings
        self.node = NodeContractApi()
        self.rate = BinanceApi("ADAUSDT")
        self.chain = ChainQuery()
        self.node_nft = (
            "e106ae90da0d5d4b155cd9477a440a043715cc24eb3996a4bee4d76f", "NodeFeed")
        self.oracle_nft = (
            "e106ae90da0d5d4b155cd9477a440a043715cc24eb3996a4bee4d76f", "OracleFeed")
        self.previous_rate = 0

    async def run(self):
        """Checks and if necesary updates and/or aggregates the contract"""
        while True:
            print(f"started at {time.strftime('%X')}")
            new_rate = asyncio.create_task(self.rate.get_rate())
            nodes_datum = asyncio.create_task(
                self.chain.get_nodes_datum(self.node_nft))
            oracle_datum = asyncio.create_task(
                self.chain.get_oracle_datum(self.oracle_nft))
            node_own_datum = self.get_node_info(nodes_datum, self.node.pkh)

            if self.check_rate_change(new_rate, node_own_datum) or self.check_time_change(node_own_datum):
                if self.check_total_nodes_updated(nodes_datum.remove(node_own_datum), oracle_datum):
                    await self.node.update_aggregate(new_rate)
                else:
                    await self.node.update(new_rate)

            elif self.check_total_nodes_updated(nodes_datum, oracle_datum):
                await self.node.aggregate()

                # if self.previous_rate > 0:
                #     rate_percentage_change = round(
                #         ((new_rate - self.previous_rate) * 100 / self.previous_rate), 2)
                # else:
                #     rate_percentage_change = 0

            print(f"finished at {time.strftime('%X')}")
            return [new_rate, nodes_datum, oracle_datum]

    def check_rate_change(self, new_rate, prev_rate):
        """check rate change condition"""

    def check_time_change(self, last_time):
        """check time change condition"""

    def check_total_nodes_updated(self, nodes_datum, oracle_datum):
        """check total nodes updated after last Aggregation"""

    def get_node_info(self, nodes_datum, pkh):
        """get node's last update information."""
