"""Sundaeswap API module"""

import logging
from typing import Optional
from charli3_offchain_core.chain_query import ChainQuery
from .coinrate import CoinRate
from .api import UnsuccessfulResponse

logger = logging.getLogger(__name__)


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
        provider_id: Optional[str] = None,
    ):
        self.provider = provider
        self.symbol = symbol
        self.quote_currency = quote_currency
        self.rate_calculation_method = rate_calculation_method
        self.provider_id = provider_id
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

    async def get_rate(
        self,
        chain_query: Optional[ChainQuery] = None,
        quote_currency_rate: Optional[float] = None,
        quote_symbol: Optional[str] = None,
    ):
        try:
            logger.info("Getting Sundaeswap %s rate", self.symbol)
            resp = await self._post(self.get_path(), self.query)
            if resp.is_ok:
                json_data = resp.json
                if (
                    json_data is not None
                    and "data" in json_data
                    and "pools" in json_data["data"]
                    and len(json_data["data"]["pools"]) > 0
                ):
                    quantity_ada = json_data["data"]["pools"][0]["quantityA"]
                    quantity_asset = json_data["data"]["pools"][0]["quantityB"]
                    base_rate = float(quantity_ada) / float(quantity_asset)
                    (rate, output_symbol) = self._calculate_final_rate(
                        self.quote_currency,
                        base_rate,
                        quote_currency_rate,
                        self.rate_calculation_method,
                        self.symbol,
                        quote_symbol,
                    )
                    logger.info("%s %s Rate: %f", self.provider, output_symbol, rate)
                    return self._construct_response_dict(
                        self.provider_id, self.get_path(), output_symbol, resp, rate
                    )
                logger.error("Invalid or missing data in JSON response")
                return self._construct_response_dict(
                    self.provider_id,
                    self.get_path(),
                    self.symbol,
                    resp,
                    None,
                    "Invalid or missing data",
                )
        except UnsuccessfulResponse as e:  # pylint: disable=invalid-name
            logger.error("Failed to get rate for Sundaeswap %s: %s", self.symbol, e)
            return self._construct_response_dict(
                self.provider_id, self.get_path(), self.symbol, None, None, str(e)
            )
