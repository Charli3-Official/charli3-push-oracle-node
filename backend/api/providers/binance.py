"""Binance API rate provider"""

import logging
from typing import Any, Dict, Optional

from charli3_offchain_core.backend import UnsuccessfulResponse
from charli3_offchain_core.chain_query import ChainQuery

from .coinrate import CoinRate

logger = logging.getLogger(__name__)


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
        rate_type: str = "base",
        provider_id: Optional[str] = None,
    ):
        self.provider = provider
        self.symbol = symbol
        self.quote_currency = quote_currency
        self.rate_calculation_method = rate_calculation_method
        self.rate_type = rate_type
        self.provider_id = provider_id

    def get_path(self):
        return self.path + self.symbol

    async def get_rate(
        self,
        chain_query: Optional[ChainQuery] = None,
        quote_currency_rate: Optional[float] = None,
        quote_symbol: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        try:
            logger.info("Getting Binance %s rate", self.symbol)
            resp = await self._get(self.get_path())

            if resp.is_ok:
                json_data = resp.json
                if json_data is not None and "price" in json_data:
                    base_rate = float(json_data["price"])
                    (rate, output_symbol) = self._calculate_final_rate(
                        self.quote_currency,
                        base_rate,
                        quote_currency_rate,
                        self.rate_calculation_method,
                        self.symbol,
                        quote_symbol,
                    )
                    logger.info("%s %s Rate: %s", self.provider, output_symbol, rate)
                    return self._construct_response_dict(
                        self.provider_id,
                        self.get_path(),
                        output_symbol,
                        self.rate_type,
                        resp,
                        rate,
                    )
            else:
                logger.error("Response not OK for Binance %s", self.symbol)
                return self._construct_response_dict(
                    self.provider_id,
                    self.get_path(),
                    self.symbol,
                    self.rate_type,
                    resp,
                    None,
                    "Response not OK",
                )
        except UnsuccessfulResponse as e:  # pylint: disable=invalid-name
            logger.error("Failed to get rate for Binance %s: %s", self.symbol, e)
            return self._construct_response_dict(
                self.provider_id,
                self.get_path(),
                self.symbol,
                self.rate_type,
                None,
                None,
                str(e),
            )
