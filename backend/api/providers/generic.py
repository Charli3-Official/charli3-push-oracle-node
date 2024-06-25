"""Generic API class for fetching exchange rates."""

import logging
from typing import Any, Dict, Optional

from charli3_offchain_core.backend import UnsuccessfulResponse
from charli3_offchain_core.chain_query import ChainQuery

from .coinrate import CoinRate

logger = logging.getLogger(__name__)


class Generic(CoinRate):
    """Abstracts the calls to exchange API's."""

    def __init__(
        self,
        provider: str,
        symbol: str,
        api_url: str,
        path: str,
        json_path: list[str | int],
        key: Optional[Dict[Any, Any]] = None,
        quote_currency: bool = False,
        rate_calculation_method: str = "multiply",
        rate_type: str = "base",
        token: Optional[str] = None,
        provider_id: Optional[str] = None,
    ):
        self.provider = provider
        self.symbol = symbol
        self.api_url = api_url
        self.path = path
        self.json_path = json_path
        self.key = {} if not key else key
        self.quote_currency = quote_currency
        self.rate_calculation_method = rate_calculation_method
        self.rate_type = rate_type
        self.token = token
        self.provider_id = provider_id

    def get_path(self) -> str:
        return self.path

    async def get_rate(
        self,
        chain_query: Optional[ChainQuery] = None,
        quote_currency_rate: Optional[float] = None,
        quote_symbol: Optional[str] = None,
    ):
        try:
            logger.info("Getting %s %s rate", self.provider, self.symbol)
            headers = self.key
            if self.token:
                # handle bearer token
                headers["Authorization"] = f"Bearer {self.token}"
            resp = await self._get(self.path, headers=headers)

            if resp and resp.is_ok:
                data = self._extract_data_from_response(resp.json)
                if data is not None:
                    (rate, output_symbol) = self._calculate_final_rate(
                        self.quote_currency,
                        float(data),
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
                    logger.error(
                        "Data at the end of JSON path is not a number or numeric string"
                    )
                    return self._construct_response_dict(
                        self.provider_id,
                        self.get_path(),
                        self.symbol,
                        self.rate_type,
                        resp,
                        None,
                        "Data at the end of JSON path is not a number or numeric string",
                    )

            else:
                error_msg = (
                    "Failed to retrieve data"
                    if not resp
                    else "Data at the end of JSON path is not a number or numeric string"
                )
                logger.error(error_msg)
                return self._construct_response_dict(
                    self.provider_id,
                    self.get_path(),
                    self.symbol,
                    self.rate_type,
                    resp if resp else None,
                    None,
                    error_msg,
                )

        except UnsuccessfulResponse as e:
            logger.error(
                "Failed to get rate for %s %s: %s", self.provider, self.symbol, e
            )
            return self._construct_response_dict(
                self.provider_id,
                self.get_path(),
                self.symbol,
                self.rate_type,
                None,
                None,
                str(e),
            )
        except Exception as e:
            logger.error(
                "Unexpected error when fetching rate: %s from %s", e, self.provider
            )
            return self._construct_response_dict(
                self.provider_id,
                self.get_path(),
                self.symbol,
                self.rate_type,
                None,
                None,
                "Unexpected error",
            )

    def _extract_data_from_response(
        self, response_data: Dict[str, Any]
    ) -> Optional[float]:
        try:
            # Navigate through the response data using the json_path
            for key in self.json_path:
                if isinstance(response_data, dict) and key in response_data:
                    response_data = response_data[key]
                elif (
                    isinstance(response_data, list)
                    and isinstance(key, int)
                    and 0 <= key < len(response_data)
                ):
                    response_data = response_data[key]
                else:
                    logger.error("Invalid path in JSON response for key: %s", key)
                    return None

            # Ensure the final data point is a valid float
            if isinstance(response_data, (int, float, str)):
                return float(response_data)
            else:
                logger.error(
                    "Data at the end of JSON path is not a number or numeric string"
                )
                return None
        except (TypeError, ValueError) as e:
            logger.error("Error processing JSON path: %s", e)
            return None
