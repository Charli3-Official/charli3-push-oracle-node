"""CoinRate classes testing"""

import json

import pytest
import sure  # pylint: disable=unused-import
from mocket import async_mocketize
from mocket.plugins.httpretty import httpretty

from backend.api.providers import (
    BinanceApi,
    CoingeckoApi,
    Generic,
    InverseCurrencyRate,
    MinswapApi,
    MuesliswapApi,
    SundaeswapApi,
    WingridersApi,
)

coinApis = {
    "binance_adausd": BinanceApi("ADA", "ADAUSDT"),
    "coingecko_adausd": CoingeckoApi("ADA", "cardano", "usd"),
    "coinmarketcap_adausd": Generic(
        "adausdt",
        "coinmarkecap",
        "https://pro-api.coinmarketcap.com",
        "/v1/cryptocurrency/quotes/latest?symbol=ADA",
        ["data", "ADA", "quote", "USD", "price"],
        {"X-CMC_PRO_API_KEY": "asdf"},
    ),
    "sundaeswap_adausd": SundaeswapApi("ADA", "ADAUSDT", "f302"),
    "minswap_adausd": MinswapApi(
        "ADA",
        "MIN",
        6,
        "SHEN",
        6,
        "53225313968e796f2c1e0b57540a13c3b81e06e2ed2637ac1ea9b9f4e27e3dc4",
    ),
    "muesliswap_adausd": MuesliswapApi(
        "ADA",
        "ADAUSDT",
        "8e51398904a5d3fc129fbf4f1589701de23c7824d5c90fdb9490e15a",
        "434841524c4933",
    ),
    "wingriders_adausd": WingridersApi(
        "ADA",
        "ADAUSDT",
        "8e51398904a5d3fc129fbf4f1589701de23c7824d5c90fdb9490e15a",
        "434841524c4933",
    ),
    "inverse_adausd": InverseCurrencyRate("ADA", "ADAUSDT"),
}


@pytest.mark.asyncio
class TestCoinRateClasses:
    """Coin Rate classes testing"""

    ex_price = 0.47039482
    ex_price_double = 0.485228513411705

    def register_api_uri(self, url, body):
        """Helper method to mock http endpoints"""
        httpretty.register_uri(
            httpretty.GET,
            url,
            body=json.dumps(body),
            **{"Content-Type": "application/json"},
        )

    def register_post_api_uri(self, url, body):
        """Helper method to mock http endpoints"""
        httpretty.register_uri(
            httpretty.POST,
            url,
            body=json.dumps(body),
            **{"Content-Type": "application/json"},
        )

    @async_mocketize(strict_mode=True)
    async def test_binance(self):
        """Binance correct functionality test"""
        api = coinApis["binance_adausd"]
        self.register_api_uri(
            f"{api.api_url}{api.get_path()}", {"mins": 5, "price": str(self.ex_price)}
        )
        data = await api.get_rate()

        # Ensure 'data' is a dictionary and contains the 'rate' key
        assert isinstance(data, dict), "Expected 'data' to be a dictionary"
        assert "rate" in data, "'rate' key not found in the 'data' dictionary"

        # Now, compare the rate from the 'data' dictionary to the expected price
        actual_rate = data["rate"]
        actual_rate.should.equal(self.ex_price)

    @async_mocketize(strict_mode=True)
    async def test_coingecko(self):
        """CoinGecko correct functionality test"""
        api = coinApis["coingecko_adausd"]
        self.register_api_uri(
            f"{api.api_url}{api.get_path()}", {"cardano": {"usd": self.ex_price}}
        )
        data = await api.get_rate()

        # Ensure 'data' is a dictionary and contains the 'rate' key
        assert isinstance(data, dict), "Expected 'data' to be a dictionary"
        assert "rate" in data, "'rate' key not found in the 'data' dictionary"

        # Now, compare the rate from the 'data' dictionary to the expected price
        actual_rate = data["rate"]
        actual_rate.should.equal(self.ex_price)

    @async_mocketize(strict_mode=True)
    async def test_generic(self):
        """Generic class correct functionality test"""
        bod = {
            "status": {
                "timestamp": "2022-06-13T20:44:46.669Z",
                "error_code": 0,
                "error_message": None,
                "elapsed": 31,
                "credit_count": 1,
                "notice": None,
            },
            "data": {
                "ADA": {
                    "id": 2010,
                    "name": "Cardano",
                    "symbol": "ADA",
                    "slug": "cardano",
                    "num_market_pairs": 455,
                    "date_added": "2017-10-01T00:00:00.000Z",
                    "tags": [
                        "mineable",
                        "dpos",
                        "pos",
                        "platform",
                        "research",
                        "smart-contracts",
                        "staking",
                        "cardano-ecosystem",
                        "cardano",
                        "bnb-chain",
                    ],
                    "max_supply": 45000000000,
                    "circulating_supply": 33934048405.593,
                    "total_supply": 34277702081.605,
                    "platform": {
                        "id": 1839,
                        "name": "BNB",
                        "symbol": "BNB",
                        "slug": "bnb",
                        "token_address": "0x3ee2200efb3400fabb9aacf31297cbdd1d435d47",
                    },
                    "is_active": 1,
                    "cmc_rank": 7,
                    "is_fiat": 0,
                    "self_reported_circulating_supply": None,
                    "self_reported_market_cap": None,
                    "last_updated": "2022-06-13T20:43:00.000Z",
                    "quote": {
                        "USD": {
                            "price": self.ex_price_double,
                            "volume_24h": 2520082937.9614344,
                            "volume_change_24h": 70.9134,
                            "percent_change_1h": 1.92465913,
                            "percent_change_24h": -6.62509015,
                            "percent_change_7d": -19.39298701,
                            "percent_change_30d": -6.34953379,
                            "percent_change_60d": -47.88610267,
                            "percent_change_90d": -39.85166946,
                            "market_cap": 16465767861.886728,
                            "market_cap_dominance": 1.6797,
                            "fully_diluted_market_cap": 21835283103.53,
                            "last_updated": "2022-06-13T20:43:00.000Z",
                        }
                    },
                }
            },
        }
        api = coinApis["coinmarketcap_adausd"]
        self.register_api_uri(f"{api.api_url}{api.get_path()}", bod)
        data = await api.get_rate()

        # Ensure 'data' is a dictionary and contains the 'rate' key
        assert isinstance(data, dict), "Expected 'data' to be a dictionary"
        assert "rate" in data, "'rate' key not found in the 'data' dictionary"

        # Now, compare the rate from the 'data' dictionary to the expected price
        actual_rate = data["rate"]
        actual_rate.should.equal(round(self.ex_price_double, 8))

    @async_mocketize(strict_mode=True)
    async def test_sundaeswap(self):
        """Sundaeswap correct functionality test"""
        api = coinApis["sundaeswap_adausd"]
        self.register_post_api_uri(
            f"{api.api_url}{api.get_path()}",
            {
                "data": {
                    "poolByIdent": {
                        "quantityA": "765813062249",
                        "quantityB": "1874892638060",
                    },
                }
            },
        )
        data = await api.get_rate()

        # Ensure 'data' is a dictionary and contains the 'rate' key
        assert isinstance(data, dict), "Expected 'data' to be a dictionary"
        assert "rate" in data, "'rate' key not found in the 'data' dictionary"

        # Now, compare the rate from the 'data' dictionary to the expected price
        actual_rate = data["rate"]
        actual_rate.should.equal(round(float(765813062249 / 1874892638060), 8))

    @async_mocketize(strict_mode=True)
    async def test_muesliswap(self):
        """Muesliswap correct functionality test"""
        api = coinApis["muesliswap_adausd"]
        self.register_api_uri(
            f"{api.api_url}{api.get_path()}", {"price": str(self.ex_price)}
        )
        data = await api.get_rate()

        # Ensure 'data' is a dictionary and contains the 'rate' key
        assert isinstance(data, dict), "Expected 'data' to be a dictionary"
        assert "rate" in data, "'rate' key not found in the 'data' dictionary"

        # Now, compare the rate from the 'data' dictionary to the expected price
        actual_rate = data["rate"]
        actual_rate.should.equal(self.ex_price)

    # @async_mocketize(strict_mode=True)
    # async def test_minswap(self):
    #     """Minswap correct functionality test"""
    #     api = coinApis["minswap_adausd"]
    #     self.register_post_api_uri(
    #         f"{api.api_url}{api.get_path()}",
    #         {
    #             "data": {
    #                 "poolByPair": {
    #                     "reserveA": 276854305370,
    #                     "reserveB": 684608590969,
    #                 }
    #             }
    #         },
    #     )
    #     data = await api.get_rate()
    #     data.should.equal(round(float(276854305370 / 684608590969), 8))

    @async_mocketize(strict_mode=True)
    async def test_inverse_rate(self):
        """Inverse rate test"""
        api = coinApis["inverse_adausd"]
        QUOTE_CURRENCY_RATE = 2.0  # pylint: disable=invalid-name
        EXPECTED_RATE = 0.5  # 1 / 2.0 pylint: disable=invalid-name

        data = await api.get_rate(quote_currency_rate=QUOTE_CURRENCY_RATE)

        assert (
            data["rate"] == EXPECTED_RATE
        ), f"Expected rate to be {EXPECTED_RATE}, but got {data}"

    @async_mocketize(strict_mode=True)
    async def test_inverse_rate_with_zero_quote_currency_rate(self):
        """Inverse rate test with zero quote currency rate"""
        api = coinApis["inverse_adausd"]
        quote_currency_rate = 0.0

        with pytest.raises(
            ValueError,
            match="quote_currency_rate cannot be zero when quote_currency is True",
        ):
            await api.get_rate(quote_currency_rate=quote_currency_rate)

    @async_mocketize(strict_mode=True)
    async def test_inverse_rate_with_int_zero_quote_currency_rate(self):
        """Inverse rate test with int zero quote currency rate"""
        api = coinApis["inverse_adausd"]
        quote_currency_rate = 0

        with pytest.raises(
            ValueError,
            match="quote_currency_rate cannot be zero when quote_currency is True",
        ):
            await api.get_rate(quote_currency_rate=quote_currency_rate)
