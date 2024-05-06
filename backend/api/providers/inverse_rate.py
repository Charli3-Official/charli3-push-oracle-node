"""This module contains the InverseCurrencyRate class, which is used to handle the inverse of the currency rate"""

import logging
from typing import Optional

from charli3_offchain_core.chain_query import ChainQuery

from .api import UnsuccessfulResponse
from .coinrate import CoinRate

logger = logging.getLogger(__name__)


class InverseCurrencyRate(CoinRate):
    """handle the inverse of the currency rate"""

    def __init__(
        self,
        provider: str,
        symbol: str,
        quote_currency: bool = True,
        rate_calculation_method: str = "divide",
        provider_id: Optional[str] = None,
    ):
        self.provider = provider
        self.symbol = symbol
        self.quote_currency = quote_currency
        self.rate_calculation_method = rate_calculation_method
        self.provider_id = provider_id

    async def get_rate(
        self,
        chain_query: ChainQuery = None,
        quote_currency_rate: Optional[float] = None,
        quote_symbol: Optional[str] = None,
    ):
        try:
            logger.info("Getting %s rate", self.symbol)
            if quote_currency_rate is not None:
                (rate, output_symbol) = self._calculate_final_rate(
                    self.quote_currency,
                    base_rate=1,
                    quote_currency_rate=quote_currency_rate,
                    rate_calculation_method=self.rate_calculation_method,
                    base_symbol=self.symbol,
                    quote_symbol=quote_symbol,
                )
                logger.info("%s %s Rate: %s", self.provider, output_symbol, rate)
                return self._construct_response_dict(
                    self.provider_id, self.symbol, output_symbol, None, rate
                )
        except UnsuccessfulResponse:
            return self._construct_response_dict(
                self.provider_id,
                self.symbol,
                self.symbol,
                None,
                None,
                "Failed to get rate",
            )
