"""This module abstracts the coingecko API"""

import logging
from typing import Optional
from charli3_offchain_core.chain_query import ChainQuery
from .coinrate import CoinRate
from .api import UnsuccessfulResponse

logger = logging.getLogger(__name__)


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
        provider_id: Optional[str] = None,
    ):
        self.provider = provider
        self.tid = tid
        self.vs_currency = vs_currency
        self.quote_currency = quote_currency
        self.rate_calculation_method = rate_calculation_method
        self.provider_id = provider_id

    def get_path(self):
        return self.path_f.format(self.tid, self.vs_currency)

    async def get_rate(
        self,
        chain_query: Optional[ChainQuery] = None,
        quote_currency_rate: Optional[float] = None,
        quote_symbol: Optional[str] = None,
    ):
        try:
            logger.info("Getting coingecko %s-%s rate", self.tid, self.vs_currency)
            resp = await self._get(self.get_path())

            if resp.is_ok:
                json_data = resp.json
                if (
                    json_data is not None
                    and self.tid in json_data
                    and self.vs_currency in json_data[self.tid]
                ):
                    base_rate = float(json_data[self.tid][self.vs_currency])
                    (rate, output_symbol) = self._calculate_final_rate(
                        self.quote_currency,
                        base_rate,
                        quote_currency_rate,
                        self.rate_calculation_method,
                        self.tid + "-" + self.vs_currency,
                        quote_symbol,
                    )
                    logger.debug("%s %s Rate: %s", self.provider, output_symbol, rate)
                    return self._construct_response_dict(
                        self.provider_id, self.get_path(), output_symbol, resp, rate
                    )
                logger.error(
                    "Invalid or missing data in JSON response for %s-%s",
                    self.tid,
                    self.vs_currency,
                )
                return self._construct_response_dict(
                    self.provider_id,
                    self.get_path(),
                    self.tid + "-" + self.vs_currency,
                    resp,
                    None,
                    "Invalid or missing data in JSON response",
                )
        except UnsuccessfulResponse as e:  # pylint: disable=invalid-name
            logger.error("Failed to get rate for coingecko %s: %s", self.tid, e)
            return self._construct_response_dict(
                self.get_path(), self.tid + "-" + self.vs_currency, None, None, str(e)
            )
