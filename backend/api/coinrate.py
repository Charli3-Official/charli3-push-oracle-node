"""Exchange Api classes."""
from typing import Optional, List
import logging
import asyncio
import json
from charli3_offchain_core.consensus import random_median
from .api import Api, UnsuccessfulResponse
from ..utils.decrypt import decrypt_response

logger = logging.getLogger("CoinRate")


class CoinRate(Api):
    """Abstract coinRate class"""

    def get_path(self):
        """Path encapsulation"""

    async def get_rate(self):
        """Returns the rate accoirding to the classes instance"""

    def _calculate_final_rate(
        self,
        quote_currency: bool,
        base_rate: float,
        quote_currency_rate: float,
        rate_calculation_method: str,
    ) -> float:
        """Calculates the final rate to be returned with the correct precision"""
        if quote_currency:
            if quote_currency_rate:
                if rate_calculation_method == "multiply":
                    rate = base_rate * quote_currency_rate
                elif rate_calculation_method == "divide":
                    if quote_currency_rate == 0:
                        raise ValueError(
                            "quote_currency_rate cannot be zero when rate_calculation_method is 'divide'"
                        )
                    rate = base_rate / quote_currency_rate
            else:
                raise ValueError(
                    "quote_currency_rate cannot be zero when quote_currency is True"
                )
        else:
            rate = base_rate
        rate = round(rate, 8)
        return rate


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
        quote_currency: bool = False,
        rate_calculation_method: str = "multiply",
        token: Optional[str] = None,
    ):
        self.provider = provider
        self.symbol = symbol
        self.api_url = api_url
        self.path = path
        self.json_path = json_path
        self.key = {} if not key else key
        self.quote_currency = quote_currency
        self.rate_calculation_method = rate_calculation_method
        self.token = token

    def get_path(self) -> str:
        return self.path

    async def get_rate(self, quote_currency_rate: float = None) -> Optional[float]:
        try:
            logger.info("Getting %s %s rate", self.provider, self.symbol)
            headers = self.key
            if self.token:
                # handle bearer token
                headers["Authorization"] = f"Bearer {self.token}"
            resp = await self._get(self.path, headers=headers)
            data = resp.json
            for key in self.json_path:
                data = data[key]
            if resp.is_ok:
                rate = self._calculate_final_rate(
                    self.quote_currency,
                    float(data),
                    quote_currency_rate,
                    self.rate_calculation_method,
                )
                logger.debug("Rate: %s", rate)
                return rate
        except UnsuccessfulResponse as e:  # pylint: disable=invalid-name
            logger.error(
                "Failed to get rate for %s %s: %s", self.provider, self.symbol, e
            )
            return None


class BinanceApi(CoinRate):
    """Abstracts the binance API rate"""

    api_url = "https://api.binance.com"
    path = "/api/v3/ticker/price?symbol="

    def __init__(
        self,
        provider: str,
        symbol: str,
        quote_currency: bool = False,
        rate_calculation_method: str = "multiply",
    ):
        self.provider = provider
        self.symbol = symbol
        self.quote_currency = quote_currency
        self.rate_calculation_method = rate_calculation_method

    def get_path(self):
        return self.path + self.symbol

    async def get_rate(self, quote_currency_rate: float = None):
        try:
            logger.info("Getting Binance %s rate", self.symbol)
            resp = await self._get(self.get_path())
            if resp.is_ok:
                base_rate = float(resp.json["price"])
                rate = self._calculate_final_rate(
                    self.quote_currency,
                    base_rate,
                    quote_currency_rate,
                    self.rate_calculation_method,
                )
                logger.debug("%s Rate: %s", self.symbol, rate)
                return rate
        except UnsuccessfulResponse as e:  # pylint: disable=invalid-name
            logger.error("Failed to get rate for Binance %s: %s", self.symbol, e)
            return None


class CoingeckoApi(CoinRate):
    """Abstracts the coingecko API"""

    api_url = "https://api.coingecko.com"
    path_f = "/api/v3/simple/price?ids={}&vs_currencies={}"

    def __init__(
        self,
        provider: str,
        tid: str,
        vs_currency: str,
        quote_currency: bool = False,
        rate_calculation_method: str = "multiply",
    ):
        self.provider = provider
        self.tid = tid
        self.vs_currency = vs_currency
        self.quote_currency = quote_currency
        self.rate_calculation_method = rate_calculation_method

    def get_path(self):
        return self.path_f.format(self.tid, self.vs_currency)

    async def get_rate(self, quote_currency_rate: float = None):
        try:
            logger.info("Getting coingecko %s-%s rate", self.tid, self.vs_currency)
            resp = await self._get(self.get_path())
            if resp.is_ok:
                base_rate = float(resp.json[self.tid][self.vs_currency])
                rate = self._calculate_final_rate(
                    self.quote_currency,
                    base_rate,
                    quote_currency_rate,
                    self.rate_calculation_method,
                )
                logger.debug("%s-%s Rate: %f", self.tid, self.vs_currency, rate)
                return rate
        except UnsuccessfulResponse as e:  # pylint: disable=invalid-name
            logger.error("Failed to get rate for coingecko %s: %s", self.tid, e)
            return None


class SundaeswapApi(CoinRate):
    """Abstracts the Sundaeswap API"""

    api_url = "https://stats.sundaeswap.finance"
    path = "/graphql"

    def __init__(
        self,
        provider: str,
        symbol: str,
        quote_currency: bool = False,
        rate_calculation_method: str = "multiply",
    ):
        self.provider = provider
        self.symbol = symbol
        self.quote_currency = quote_currency
        self.rate_calculation_method = rate_calculation_method
        self.query = {
            "query": """
            query searchPools($query: String!) {
              pools(query: $query) {
                ...PoolFragment
              }
            }

            fragment PoolFragment on Pool {
              assetA {
                ...AssetFragment
              }
              assetB {
                ...AssetFragment
              }
              assetLP {
                ...AssetFragment
              }
              fee
              quantityA
              quantityB
              quantityLP
              ident
              assetID
            }

            fragment AssetFragment on Asset {
              assetId
              policyId
              assetName
              decimals
            }
        """,
            "variables": {"query": self.symbol},
            "operationName": "searchPools",
        }

    def get_path(self):
        return self.path

    async def get_rate(self, quote_currency_rate: float = None):
        try:
            logger.info("Getting Sundaeswap %s rate", self.symbol)
            resp = await self._post(self.get_path(), self.query)
            if resp.is_ok:
                quantity_ada = resp.json["data"]["pools"][0]["quantityA"]
                quantity_asset = resp.json["data"]["pools"][0]["quantityB"]
                base_rate = float(quantity_ada) / float(quantity_asset)
                rate = self._calculate_final_rate(
                    self.quote_currency,
                    base_rate,
                    quote_currency_rate,
                    self.rate_calculation_method,
                )
                logger.info("%s-%s Rate: %f", self.provider, self.symbol, rate)
                return rate
        except UnsuccessfulResponse as e:  # pylint: disable=invalid-name
            logger.error("Failed to get rate for Sundaeswap %s: %s", self.symbol, e)
            return None


class MinswapApi(CoinRate):
    """Abstracts the minswap API"""

    api_url = "https://monorepo-mainnet-prod.minswap.org"
    path = "/graphql?PoolByPair"

    def __init__(
        self,
        provider: str,
        symbol: str,
        currency_symbol: str,
        token_name: str,
        quote_currency: bool = False,
        rate_calculation_method: str = "multiply",
    ):
        self.provider = provider
        self.symbol = symbol
        self.currency_symbol = currency_symbol
        self.token_name = token_name
        self.quote_currency = quote_currency
        self.rate_calculation_method = rate_calculation_method
        self.query = {
            "query": """
            query PoolByPair($pair: InputPoolByPair!) {
              poolByPair(pair: $pair) {
                assetA {
                  currencySymbol
                  tokenName
                  isVerified
                }
                assetB {
                  currencySymbol
                  tokenName
                  isVerified
                }
                reserveA
                reserveB
                lpAsset {
                  currencySymbol
                  tokenName
                }
                totalLiquidity
              }
            }
        """,
            "variables": {
                "pair": {
                    "assetA": {"currencySymbol": "", "tokenName": ""},
                    "assetB": {
                        "currencySymbol": self.currency_symbol,
                        "tokenName": self.token_name,
                    },
                },
                "useCache": False,
            },
        }

    def get_path(self):
        return self.path

    async def get_rate(self, quote_currency_rate: float = None):
        try:
            logger.info("Getting Minswap %s rate", self.symbol)
            resp = await self._post(self.get_path(), self.query)
            if resp.is_ok:
                decrypted_response = decrypt_response(
                    resp.json["data"]["encryptedData"]
                )
                response_data = json.loads(decrypted_response)
                quantity_ada = response_data["data"]["poolByPair"]["reserveA"]
                quantity_asset = response_data["data"]["poolByPair"]["reserveB"]
                base_rate = float(quantity_ada) / float(quantity_asset)
                rate = self._calculate_final_rate(
                    self.quote_currency,
                    base_rate,
                    quote_currency_rate,
                    self.rate_calculation_method,
                )
                logger.info("%s-%s Rate: %f", self.provider, self.symbol, rate)
                return rate
        except UnsuccessfulResponse as e:  # pylint: disable=invalid-name
            logger.error("Failed to get rate for Minswap %s: %s", self.symbol, e)
            return None


class WingridersApi(CoinRate):
    """Abstracts the Wingriders API"""

    api_url = "https://api.mainnet.wingriders.com"
    path = "/graphql"

    def __init__(
        self,
        provider: str,
        symbol: str,
        currency_symbol: str,
        token_name: str,
        quote_currency: bool = False,
        rate_calculation_method: str = "multiply",
    ):
        self.provider = provider
        self.symbol = symbol
        self.asset_id = currency_symbol + token_name
        self.quote_currency = quote_currency
        self.rate_calculation_method = rate_calculation_method
        self.query = {
            "operationName": "AssetsAdaExchangeRates",
            "variables": {},
            "query": """query AssetsAdaExchangeRates {
                                assetsAdaExchangeRates {
                                    ...AssetExchangeRateFragment
                                    __typename
                                }
                            }

                            fragment AssetExchangeRateFragment on AssetExchangeRate {
                                assetId
                                baseAssetId
                                exchangeRate
                                __typename
                        }""",
        }

    def get_path(self):
        return self.path

    async def get_rate(self, quote_currency_rate: float = None):
        try:
            logger.info("Getting Wingriders %s rate", self.symbol)
            resp = await self._post(self.get_path(), self.query)
            if resp.is_ok:
                for asset in resp.json["data"]["assetsAdaExchangeRates"]:
                    if asset["assetId"] == self.asset_id:
                        base_rate = float(asset["exchangeRate"])
                        rate = self._calculate_final_rate(
                            self.quote_currency,
                            base_rate,
                            quote_currency_rate,
                            self.rate_calculation_method,
                        )
                        logger.info("%s-%s Rate: %f", self.provider, self.symbol, rate)
                        return rate
                logger.debug("%s-%s Rate: %f", self.provider, self.symbol, rate)
                return rate
        except UnsuccessfulResponse as e:  # pylint: disable=invalid-name
            logger.error("Failed to get rate for Wingriders %s: %s", self.symbol, e)
            return None


class MuesliswapApi(CoinRate):
    """Abstracts the Muesliswap API"""

    api_url = "https://api.muesliswap.com"
    path = "/price?base-policy-id=&base-tokenname=&"

    def __init__(
        self,
        provider: str,
        symbol: str,
        currency_symbol: str,
        token_name: str,
        quote_currency: bool = False,
        rate_calculation_method: str = "multiply",
    ):
        self.provider = provider
        self.symbol = symbol
        self.quote_currency = quote_currency
        self.rate_calculation_method = rate_calculation_method
        self.additional_path = (
            self.path
            + "quote-policy-id="
            + currency_symbol
            + "&quote-tokenname="
            + token_name
        )

    def get_path(self):
        return self.path + self.additional_path

    async def get_rate(self, quote_currency_rate: float = None):
        try:
            logger.info("Getting Muesliswap %s rate", self.symbol)
            resp = await self._get(self.get_path())
            if resp.is_ok:
                base_rate = float(resp.json["price"])
                rate = self._calculate_final_rate(
                    self.quote_currency,
                    base_rate,
                    quote_currency_rate,
                    self.rate_calculation_method,
                )
                logger.info("%s-%s Rate: %f", self.provider, self.symbol, rate)
                return rate
        except UnsuccessfulResponse as e:  # pylint: disable=invalid-name
            logger.error("Failed to get rate for Muesliswap %s: %s", self.symbol, e)
            return None


class InverseCurrencyRate(CoinRate):
    """handle the inverse of the currency rate"""

    def __init__(
        self,
        provider: str,
        symbol: str,
        quote_currency: bool = True,
        rate_calculation_method: str = "divide",
    ):
        self.provider = provider
        self.symbol = symbol
        self.quote_currency = quote_currency
        self.rate_calculation_method = rate_calculation_method

    async def get_rate(self, quote_currency_rate: float = None):
        try:
            logger.info("Getting %s rate", self.symbol)
            if quote_currency_rate is not None:
                rate = self._calculate_final_rate(
                    self.quote_currency,
                    base_rate=1,
                    quote_currency_rate=quote_currency_rate,
                    rate_calculation_method=self.rate_calculation_method,
                )
                logger.info("%s Rate: %f", self.symbol, rate)
                return rate
        except UnsuccessfulResponse:
            return None


apiTypes = {
    "generic": Generic,
    "binance": BinanceApi,
    "coingecko": CoingeckoApi,
    "sundaeswap": SundaeswapApi,
    "minswap": MinswapApi,
    "wingriders": WingridersApi,
    "muesliswap": MuesliswapApi,
    "inverserate": InverseCurrencyRate,
}


class AggregatedCoinRate:
    """Handles rate review on market"""

    def __init__(self, quote_currency: bool = False):
        self.quote_currency = quote_currency
        self.base_data_providers = []
        self.quote_data_providers = []

    def add_base_data_provider(self, feed_type, provider, pair):
        """add provider to list."""
        self.base_data_providers.append(apiTypes[feed_type](provider, **pair))

    def add_quote_data_provider(self, feed_type, provider, pair):
        """add provider to list."""
        self.quote_data_providers.append(apiTypes[feed_type](provider, **pair))

    async def get_rate_from_providers(
        self, providers: List[CoinRate], quote_rate: Optional[float] = None
    ) -> Optional[float]:
        """Get rate from providers.

        Args:
            providers (List[CoinRate]): list of providers
            quote_rate (Optional[float], optional): quote rate. Defaults to None.

        Returns:
            Optional[float]: rate
        """
        rates_to_get = [provider.get_rate(quote_rate) for provider in providers]
        responses = await asyncio.gather(*rates_to_get, return_exceptions=True)

        valid_responses = [
            resp
            for resp in responses
            if resp is not None and not isinstance(resp, Exception)
        ]
        if not valid_responses:
            logger.critical("No data prices are available to estimate the median")
            return None

        result = random_median(valid_responses)
        logger.info("Aggregated rate calculated : %s from %s", result, valid_responses)
        return result

    async def get_aggregated_rate(self):
        """calculate aggregated rate from list of data providers."""

        quote_rate = None
        logger.info("get_aggregated_rate: fetching price from data providers")

        # Fetch Median Quote Rate first if quote_currency is True
        if self.quote_currency:
            logger.info("fetching quote price from data providers")
            quote_rate = await self.get_rate_from_providers(self.quote_data_providers)
            if quote_rate is None:
                logger.error("No valid quote rates available.")

        # Fetch Median Base Rate with quote_rate calculation if quote_currency is enabled
        base_rate = await self.get_rate_from_providers(
            self.base_data_providers, quote_rate
        )

        if base_rate is None:
            logger.error("No valid base rates available.")

        return base_rate
