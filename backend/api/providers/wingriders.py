"""Wingriders API"""

import logging
from typing import Optional
from charli3_offchain_core.chain_query import ChainQuery
from .coinrate import CoinRate
from .api import UnsuccessfulResponse

logger = logging.getLogger(__name__)


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
        provider_id: Optional[str] = None,
    ):
        self.provider = provider
        self.symbol = symbol
        self.asset_id = currency_symbol + token_name
        self.quote_currency = quote_currency
        self.rate_calculation_method = rate_calculation_method
        self.provider_id = provider_id
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

    async def get_rate(
        self,
        chain_query: Optional[ChainQuery] = None,
        quote_currency_rate: Optional[float] = None,
        quote_symbol: Optional[str] = None,
    ):
        try:
            logger.info("Getting Wingriders %s rate", self.symbol)
            resp = await self._post(self.get_path(), self.query)
            if resp.is_ok:
                json_data = resp.json
                if (
                    json_data is not None
                    and "data" in json_data
                    and "assetsAdaExchangeRates" in json_data["data"]
                ):
                    for asset in json_data["data"]["assetsAdaExchangeRates"]:
                        if asset["assetId"] == self.asset_id:
                            base_rate = float(asset["exchangeRate"])
                            (rate, output_symbol) = self._calculate_final_rate(
                                self.quote_currency,
                                base_rate,
                                quote_currency_rate,
                                self.rate_calculation_method,
                                self.symbol,
                                quote_symbol,
                            )
                            logger.info(
                                "%s %s Rate: %s",
                                self.provider,
                                output_symbol,
                                rate,
                            )
                            return self._construct_response_dict(
                                self.provider_id,
                                self.get_path(),
                                output_symbol,
                                resp,
                                rate,
                            )
                    logger.debug(
                        "Asset ID not found in response for %s-%s",
                        self.provider,
                        self.symbol,
                    )
                    return self._construct_response_dict(
                        self.provider_id,
                        self.get_path(),
                        self.symbol,
                        resp,
                        None,
                        "Asset ID not found in response",
                    )
                else:
                    logger.error("Invalid or missing JSON data in response")
                return self._construct_response_dict(
                    self.provider_id,
                    self.get_path(),
                    self.symbol,
                    resp,
                    None,
                    "Invalid or missing JSON data in response",
                )
        except UnsuccessfulResponse as e:  # pylint: disable=invalid-name
            logger.error("Failed to get rate for Wingriders %s: %s", self.symbol, e)
            return self._construct_response_dict(
                self.provider_id, self.get_path(), self.symbol, None, None, str(e)
            )
