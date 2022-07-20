"""Exchange Api classes."""
import logging
from .api import Api

logger = logging.getLogger("CoinRate")

class CoinRate(Api):
    """Abstract coinRate class"""
    def get_path(self):
        """Path encapsulation"""

    async def get_rate(self):
        """Returns the rate accoirding to the classes instance"""


class Generic(CoinRate):
    """Abstracts the calls to exchange API's."""
    def __init__(self,
                 api_url: str,
                 path: str,
                 json_path: list[str|int],
                 key: dict=None):
        self.api_url = api_url
        self.path = path
        self.json_path = json_path
        self.key = {} if not key else key

    def get_path(self):
        return self.path

    async def get_rate(self):
        logger.info("Getting generic rate")
        resp = await self._get(
            self.path,
            headers=self.key
            )
        data = resp.json
        for key in self.json_path:
            data = data[key]
        if resp.is_ok:
            rate = float(data)
            logger.debug("Rate: %s", rate)
            return rate
        return None


class BinanceApi(CoinRate):
    """Abstracts the binance API rate"""
    api_url = "https://api.binance.com"
    path = "/api/v3/avgPrice?symbol="
    def __init__(self, symbol: str):
        self.symbol = symbol

    def get_path(self):
        return self.path+self.symbol

    async def get_rate(self):
        logger.info("Getting Binance %s rate", self.symbol)
        resp = await self._get(
            self.get_path()
            )
        if resp.is_ok:
            rate = float(resp.json["price"])
            logger.debug("%s Rate: %s", self.symbol, rate)
            return rate
        return None


class CoingeckoApi(CoinRate):
    """Abstracts the coingecko API"""
    api_url="https://api.coingecko.com"
    path_f = "/api/v3/simple/price?ids={}&vs_currencies={}"
    def __init__(self, tid: str, vs_currency: str):
        self.tid = tid
        self.vs_currency = vs_currency

    def get_path(self):
        return self.path_f.format(self.tid, self.vs_currency)

    async def get_rate(self):
        logger.info("Getting coingecko %s-%s rate", self.tid, self.vs_currency)
        resp = await self._get(
            self.get_path()
            )
        if resp.is_ok:
            rate = resp.json[self.tid][self.vs_currency]
            logger.debug("%s-%s Rate: %f", self.tid, self.vs_currency, rate)
            return rate
        return None


apiTypes = {
    "generic": Generic,
    "binance": BinanceApi,
    "coingecko": CoingeckoApi
}
