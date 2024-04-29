"""Exchange Api classes."""

from typing import Optional, Any, Dict, Tuple
import logging
import re

from .api import Api, ApiResponse

logger = logging.getLogger("CoinRate")


class CoinRate(Api):
    """Abstract coinRate class"""

    def get_path(self):
        """Path encapsulation"""

    async def get_rate(
        self, chain_query=None, quote_currency_rate=None, quote_symbol=None
    ) -> Optional[Dict[str, Any]]:
        """Returns the rate accoirding to the classes instance"""
        raise NotImplementedError("get_rate method must be implemented")

    def _get_final_symbol(
        self, base_symbol, quote_symbol: Optional[str], method
    ) -> str:
        """
        Constructs and returns a currency symbol based on the base and quote symbols and the method.
        If only one symbol is provided, it returns that symbol.
        If both are provided, it constructs a symbol based on the method ('multiply' or 'divide').
        """
        if not base_symbol:
            raise ValueError("Base symbol is required")

        # Pattern to match symbols with '-', '/', ' - ', ' / ', or ' ' as separators
        pattern = r"([A-Za-z]+)\s*[-/\s]\s*([A-Za-z]+)"
        bs_match = re.match(pattern, base_symbol, re.IGNORECASE)
        qs_match = (
            re.match(pattern, quote_symbol, re.IGNORECASE) if quote_symbol else None
        )

        # Extract symbols if they match the pattern
        bs_base, _ = bs_match.groups() if bs_match else (None, None)
        qs_base, qs_quote = qs_match.groups() if qs_match else (None, None)

        # Construct symbol based on method
        if method == "multiply" and bs_base and qs_quote:
            return f"{bs_base}/{qs_quote}".upper()
        elif method == "divide" and bs_base and qs_base:
            return f"{bs_base}/{qs_base}".upper()
        else:
            return base_symbol.upper()

    def _calculate_final_rate(
        self,
        quote_currency: bool,
        base_rate: float,
        quote_currency_rate: Optional[float],
        rate_calculation_method: str,
        base_symbol: str,
        quote_symbol: Optional[str],
    ) -> Tuple[float, str]:
        """Calculates the final rate to be returned with the correct precision"""
        symbol = self._get_final_symbol(
            base_symbol, quote_symbol, rate_calculation_method
        )
        rate: float = 0
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
        return (rate, symbol)

    def _construct_response_dict(
        self,
        provider_id: str,
        path: str,
        symbol: str,
        response: Optional[ApiResponse],
        rate: Optional[float],
        error: Optional[str] = None,
    ) -> Dict[str, Any]:
        quote_currency = getattr(
            self, "quote_currency", False
        )  # Default to False if not present
        rate_type = "quote" if not quote_currency else "base"
        return {
            "provider_id": provider_id,
            "path": path,
            "symbol": symbol,
            "response_code": response.status if response else 299,
            "response_body": (str(response.json) if response else str(error)),
            "rate": rate,
            "rate_type": rate_type,
        }
