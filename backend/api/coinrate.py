#!/usr/bin/env python3
import os

from .api import Api


class CoinRate(Api):
    """Abstracts the calls to exchange API's."""
    def __init__(self,
                 api_url: str,
                 path: str,
                 json_path: list[str|int],
                 key: dict=dict()):
        self.api_url = api_url
        self.path = path
        self.json_path = json_path
        self.key = key

    def get_path(self):
        return self.path

    async def get_rate(self):
        resp = await self._request('GET', self.path, headers=self.key)
        data = resp.json
        for f in self.json_path:
            data = data[f]
        if (200<=resp.status and resp.status<300):
            return float(data)
        else:
            return None

class BinanceApi(Api):
    """Abstracts the binance API rate"""
    api_url = "https://api.binance.com"
    path = "/api/v3/avgPrice?symbol="
    def __init__(self, symbol: str):
        self.symbol = symbol

    def get_path(self):
        return self.path+self.symbol

    async def get_rate(self):
        resp = await self._request(
            'GET',
            self.get_path())
        if (200<=resp.status and resp.status<300):
            return float(resp.json["price"])
        else:
            return None

class CoingeckoApi(Api):
    """Abstracts the coingecko API"""
    api_url="https://api.coingecko.com"
    path_f = "/api/v3/simple/price?ids={}&vs_currencies={}"
    def __init__(self, tid: str, vs_currency: str):
        self.tid = tid
        self.vs_currency = vs_currency

    def get_path(self):
        return self.path_f.format(self.tid, self.vs_currency)

    async def get_rate(self):
        resp = await self._request(
            'GET',
            self.get_path(),
            )
        if (200<=resp.status and resp.status<300):
            return resp.json[self.tid][self.vs_currency]
        else:
            return None

apiTypes = {
    "generic": CoinRate,
    "binance": BinanceApi,
    "coingecko": CoingeckoApi
}

# TODO: Once we make a config file make the apis that require keys.
coinApis = {
    "binance_adausd": BinanceApi("ADAUSDT"),
    "coingecko_adausd": CoingeckoApi("cardano", "usd"),
    "coinmarketcap_adausd": CoinRate(
        "https://pro-api.coinmarketcap.com",
        "/v1/cryptocurrency/quotes/latest?symbol=ADA",
        ["data","ADA","quote","USD","price"],
        {"X-CMC_PRO_API_KEY": "asdf"} # missing a way to get the api key.
    )
}