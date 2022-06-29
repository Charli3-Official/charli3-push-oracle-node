"""Main updater class"""
import time
import asyncio
from math import ceil

from .api import NodeContractApi, CoinRate, ChainQuery
from .api.api import UnsuccessfulResponse
from .api.coinrate import BinanceApi
from .api.datums import NodeDatum, OracleDatum
from .api.node import FailedOperation, PABTimeout
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
        await self.initialize_feed()
        while True:
            try:
                print(f"started at {time.strftime('%X')}")
                start_time = time.time()
                data_coro = [
                    self.rate.get_rate(),
                    self.chain.get_nodes_datum(self.node_nft),
                    self.chain.get_oracle_datum(self.oracle_nft)
                ]
                data = await asyncio.gather(*data_coro)
                # Prepare data for usage
                new_rate = self._calculate_rate(data[0])
                # Get our datum
                node_own_datum = self.get_node_info(data[1], self.node.pkh)
                # Remove all uninitialized nodes
                nodes_datum = list(filter(
                    lambda x: x.node_feed.has_value(),
                    data[1]
                ))
                nodes_datum.remove(node_own_datum)
                oracle_datum = data[2]
                print(f"gather info finished {time.strftime('%X')}")

                nodes_updated = self.total_nodes_updated(
                    nodes_datum,
                    oracle_datum)

                own_feed = node_own_datum.node_feed
                req_nodes = self.oracle_settings.required_nodes_num()

                if (self.check_rate_change(new_rate, own_feed.value)
                        or self.is_expired(own_feed.timestamp)):
                    if nodes_updated==req_nodes-1:
                        print("UPDATE AGREGATE")
                        await self.node.update_aggregate(new_rate)
                    else:
                        print("UPDATE")
                        await self.node.update(new_rate)
                elif nodes_updated+1>=req_nodes:
                    print("Aggregate")
                    await self.node.aggregate()
                else:
                    print("Did nothing")


                print(f"finished at {time.strftime('%X')}")
                time_elapsed = time.time()-start_time

                print(f"elapsed {time_elapsed} must wait {self.update_inter-time_elapsed}")
                await asyncio.sleep(max(self.update_inter-time_elapsed,0))
                print(f"finished at {time.strftime('%X')}")
            except UnsuccessfulResponse as e:
                print(f"UnsuccessfulResponse{e}")
            except FailedOperation as e:
                print(f"FailedOperation{e}")
            except PABTimeout as e:
                print(f"PABTimeout{e}")

    async def initialize_feed(self):
        """Check that our feed is initialized and do if its not"""
        datums = await self.chain.get_nodes_datum(self.node_nft)
        own_datum = self.get_node_info(datums, self.node.pkh)
        if not own_datum.node_feed.has_value():
            rate = await self.rate.get_rate()
            await self.node.update(self._calculate_rate(rate))
            await asyncio.sleep(60)

    @staticmethod
    def _calculate_rate(rate):
        return ceil(rate*1000000)

    def check_rate_change(
            self,
            new_rate: int,
            prev_rate: int) -> bool:
        """check rate change condition"""
        res = self.oracle_settings.percent_resolution
        change = abs((new_rate*res)/prev_rate-res)
        print(f"check_rate:{change>self.oracle_settings.aggregate_change} rate={prev_rate}")
        return change>self.oracle_settings.aggregate_change

    def is_expired(
            self,
            last_time: int) -> bool:
        """check time change condition"""
        time_ms = time.time_ns()*1e-6
        timediff = time_ms-last_time
        print(f"is_expired:{timediff>self.oracle_settings.node_expiry} timediff:{timediff}")
        return timediff>self.oracle_settings.node_expiry

    def total_nodes_updated(
            self,
            nodes_datum: list[NodeDatum],
            oracle_datum: OracleDatum) -> int:
        """check total nodes updated after last Aggregation"""
        updated = len(nodes_datum)
        ofeed = oracle_datum.oracle_feed
        if ofeed.has_value():
            for dat in nodes_datum:
                timediff = dat.node_feed.timestamp-ofeed.timestamp
                if not 0 < timediff < self.oracle_settings.node_expiry:
                    updated -= 1
        return updated

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
        "de031116866f1688d288b8eb42d1c321c0a2ecaf4acb05bbf7757c02",
        ("716e6a0dc6ade9c74eae49bfb3f006e809a131d9e5f201f631f8b7d4", "CHARLI3")
    )
    n = NodeContractApi(
        o,
        "71517afc9a4d6dd79294ff6be77dd6a6a3c70d95",
        "3a1314fa60a312d41eaf203378a6a92b5fca5c6649580e0c3e4fa707")
    sett = OracleSettings(
        node_pkhs=['3a1314fa60a312d41eaf203378a6a92b5fca5c6649580e0c3e4fa707'],
        required_nodes=3500,
        node_expiry=300000,
        aggregate_time=720000,
        aggregate_change=500,
        mad_mult=20000,
        divergence=1500,
        percent_resolution=10000
    )
    a = FeedUpdater(180, sett, n, BinanceApi("ADAUSDT"),ChainQuery())
    loop = asyncio.run(a.run())
