"""Main updater class"""
import asyncio
import time

from backend.api import NodeContractApi, CoinRate, ChainQuery
from backend.api.coinrate import BinanceApi
from backend.api.datums import NodeDatum, OracleDatum
from .core.oracle import OracleSettings, Oracle


class FeedUpdater():
    """Main thread for managing a node feed"""

    def __init__(self,
                 update_inter: int,
                 oracle_settings: OracleSettings,
                 node: NodeContractApi,
                 rate: CoinRate,
                 chain: ChainQuery):
        self.update_inter = update_inter
        self.oracle_settings = oracle_settings
        self.node = node
        self.rate = rate
        self.chain = chain
        self.node_nft = self.node.oracle.get_node_feed_nft()
        self.oracle_nft = self.node.oracle.get_oracle_feed_nft()
        self.previous_rate = 0

    async def run(self):
        """Checks and if necesary updates and/or aggregates the contract"""
        await self.node.activate()
        while True:
            print(f"started at {time.strftime('%X')}")
            start_time = time.time()
            data_coro = [
                self.rate.get_rate(),
                self.chain.get_nodes_datum(self.node_nft),
                self.chain.get_oracle_datum(self.oracle_nft)
            ]
            data = await asyncio.gather(*data_coro)
            new_rate = data[0]*100000000
            nodes_datum = data[1]
            oracle_datum = data[2]
            print(f"gather info finished {time.strftime('%X')}")

            node_own_datum = self.get_node_info(nodes_datum, self.node.pkh)
            nodes_updated = self.total_nodes_updated(nodes_datum, oracle_datum)

            own_feed = node_own_datum.node_feed
            req_nodes = self.oracle_settings.required_nodes_num()

            if (self.check_rate_change(new_rate, own_feed.value)
                or self.check_time_change(own_feed.timestamp)):
                if nodes_updated==req_nodes-1:
                    await self.node.update_aggregate(new_rate)
                else:
                    await self.node.update(new_rate)

            elif nodes_updated>=req_nodes:
                await self.node.aggregate()

            print(f"finished at {time.strftime('%X')}")
            time_elapsed = time.time()-start_time

            print(f"elapsed {time_elapsed} must wait {self.update_inter-time_elapsed}")
            await asyncio.sleep(self.update_inter-time_elapsed)
            print(f"finished at {time.strftime('%X')}")

    def check_rate_change(
            self,
            new_rate: int,
            prev_rate: int) -> bool:
        """check rate change condition"""
        res = self.oracle_settings.percent_resolution
        change = (new_rate*res)/prev_rate
        return change>self.oracle_settings.aggregate_change

    def check_time_change(
            self,
            last_time: int) -> bool:
        """check time change condition"""
        timediff = time.time()-last_time
        return (timediff>self.oracle_settings.aggregate_time
                or timediff>self.oracle_settings.node_expiry)

    def total_nodes_updated(
            self,
            nodes_datum: list[NodeDatum],
            oracle_datum: OracleDatum) -> int:
        """check total nodes updated after last Aggregation"""
        valid = 0
        otime = oracle_datum.oracle_feed.timestamp
        for dat in nodes_datum:
            if dat.node_feed is not None:
                timediff = dat.node_feed.timestamp-otime
                if 0 < timediff < self.oracle_settings.node_expiry:
                    valid += 1
        return valid

    def get_node_info(
            self,
            nodes_datum: list[NodeDatum],
            pkh: str) -> NodeDatum:
        """get node's last update information."""
        for dat in nodes_datum:
            if dat.node_operator==pkh:
                return dat
        return None

if __name__=="__main__":
    o = Oracle(
        "ef097309136a1242669c29bf772b32efad68af0405f406e92a2e1ac0",
        "e106ae90da0d5d4b155cd9477a440a043715cc24eb3996a4bee4d76f",
        ("716e6a0dc6ade9c74eae49bfb3f006e809a131d9e5f201f631f8b7d4", "CHARLI3")
    )
    n = NodeContractApi(
        o,
        "71517afc9a4d6dd79294ff6be77dd6a6a3c70d95",
        "3a1314fa60a312d41eaf203378a6a92b5fca5c6649580e0c3e4fa707")
    sett = OracleSettings(
        node_pkhs=[
            '3a1314fa60a312d41eaf203378a6a92b5fca5c6649580e0c3e4fa707',
            'b2ff7b709174bfc6c65b7be977b8d7320c03f0eaa8e2f5305d1b9aad',
            '1e5d17616b1a98b8314412c980ae1feaa95b1e441ffc350b756ef8c5',
            '253aaa40bc3dee48fa41d50fb451ccf044916dc054f3041868a6ecfe',
            'f3fd66efbe0f22a66e815112c26b492edb27bda2dcd16da81832dce0'
          ],
        required_nodes=3500,
        node_expiry=300000,
        aggregate_time=720000,
        aggregate_change=500,
        mad_mult=20000,
        divergence=1500,
        percent_resolution=10000
    )
    a = FeedUpdater(300, sett, n, BinanceApi("ADAUSDT"),ChainQuery())
    loop = asyncio.run(a.run())
