"""Exchange Api classes."""
from .api import Api

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
        resp = await self._request('GET', self.path, headers=self.key)
        data = resp.json
        for key in self.json_path:
            data = data[key]
        if (200<=resp.status and resp.status<300):
            return float(data)
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
        resp = await self._request(
            'GET',
            self.get_path())
        if (200<=resp.status and resp.status<300):
            return float(resp.json["price"])
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
        resp = await self._request(
            'GET',
            self.get_path(),
            )
        if (200<=resp.status and resp.status<300):
            return resp.json[self.tid][self.vs_currency]
        return None

apiTypes = {
    "generic": Generic,
    "binance": BinanceApi,
    "coingecko": CoingeckoApi
}

# This dictionary will be removed, it is kept for the sake of exemplification
coinApis = {
    "binance_adausd": BinanceApi("ADAUSDT"),
    "coingecko_adausd": CoingeckoApi("cardano", "usd"),
    "coinmarketcap_adausd": Generic(
        "https://pro-api.coinmarketcap.com",
        "/v1/cryptocurrency/quotes/latest?symbol=ADA",
        ["data","ADA","quote","USD","price"],
        {"X-CMC_PRO_API_KEY": "asdf"} # missing a way to get the api key.
    )
}
