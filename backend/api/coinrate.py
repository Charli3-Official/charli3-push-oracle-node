"""Exchange Api classes."""
import logging
import asyncio
from .api import Api, UnsuccessfulResponse
from ..core.consensus import random_median

logger = logging.getLogger("CoinRate")


class CoinRate(Api):
    """Abstract coinRate class"""

    def get_path(self):
        """Path encapsulation"""

    async def get_rate(self):
        """Returns the rate accoirding to the classes instance"""


class Generic(CoinRate):
    """Abstracts the calls to exchange API's."""

    def __init__(
        self,
        provider: str,
        symbol: str,
        api_url: str,
        path: str,
        json_path: list[str | int],
        key: dict = None,
    ):
        self.provider = provider
        self.symbol = symbol
        self.api_url = api_url
        self.path = path
        self.json_path = json_path
        self.key = {} if not key else key

    def get_path(self):
        return self.path

    async def get_rate(self):
        try:
            logger.info("Getting %s %s rate", self.provider, self.symbol)
            resp = await self._get(self.path, headers=self.key)
            data = resp.json
            for key in self.json_path:
                data = data[key]
            if resp.is_ok:
                rate = float(data)
                logger.debug("Rate: %s", rate)
                return rate
        except UnsuccessfulResponse:
            return None


class BinanceApi(CoinRate):
    """Abstracts the binance API rate"""

    api_url = "https://api.binance.com"
    path = "/api/v3/avgPrice?symbol="

    def __init__(self, provider: str, symbol: str):
        self.provider = provider
        self.symbol = symbol

    def get_path(self):
        return self.path + self.symbol

    async def get_rate(self):
        try:
            logger.info("Getting Binance %s rate", self.symbol)
            resp = await self._get(self.get_path())
            if resp.is_ok:
                rate = float(resp.json["price"])
                logger.debug("%s Rate: %s", self.symbol, rate)
                return rate
        except UnsuccessfulResponse:
            return None


class CoingeckoApi(CoinRate):
    """Abstracts the coingecko API"""

    api_url = "https://api.coingecko.com"
    path_f = "/api/v3/simple/price?ids={}&vs_currencies={}"

    def __init__(self, provider: str, tid: str, vs_currency: str):
        self.provider = provider
        self.tid = tid
        self.vs_currency = vs_currency

    def get_path(self):
        return self.path_f.format(self.tid, self.vs_currency)

    async def get_rate(self):
        try:
            logger.info("Getting coingecko %s-%s rate", self.tid, self.vs_currency)
            resp = await self._get(self.get_path())
            if resp.is_ok:
                rate = resp.json[self.tid][self.vs_currency]
                logger.debug("%s-%s Rate: %f", self.tid, self.vs_currency, rate)
                return rate
        except UnsuccessfulResponse:
            return None


apiTypes = {"generic": Generic, "binance": BinanceApi, "coingecko": CoingeckoApi}


class AggregatedCoinRate:
    """Handles rate review on market"""

    data_providers = []

    def add_data_provider(self, feed_type, provider, pair):
        """add provider to list."""
        self.data_providers.append(apiTypes[feed_type](provider, **pair))

    async def get_aggregated_rate(self):
        """calculate aggregated rate from list of data providers."""

        rates_response = []
        logger.info("get_aggregated_rate: fetching price from data providers")

        rates_to_get = [provider.get_rate() for provider in self.data_providers]

        rates_response = await asyncio.gather(*rates_to_get)

        valid_response = list(filter(None, rates_response))

        if len(valid_response) == 0:
            logger.critical("No data prices are available to estimate the median")
            result = None
        else:
            result = random_median(valid_response)

        logger.info(
            "Aggregated rate calculated : %s from %s",
            result,
            rates_response,
            extra={"tag": "market_rates", "median": result, "market": rates_response},
        )
        return result
