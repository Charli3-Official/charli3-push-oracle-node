import asyncio
import logging
from typing import Any, Optional, Tuple, Union

import aiohttp

from backend.api.providers.base_adapter import BaseAdapter

logger = logging.getLogger(__name__)


class GenericApiAdapter(BaseAdapter):
    """
    Generic API adapter to fetch rates for an asset pair across multiple API sources.
    """

    def __init__(
        self,
        asset_a: str,
        asset_b: str,
        pair_type: str,
        sources: Optional[list[dict[str, Any]]] = None,
        quote_required: Optional[bool] = False,
        quote_calc_method: Optional[str] = None,
    ) -> None:
        """Constructor for the GenericApiAdapter class.

        Args:
            asset_a (str): The name of asset A (base token).
            asset_b (str): The name of asset B (quote token).
            sources (list[dict[str, Any]]): A list of sources to fetch rates from, each including:
                - name (str): The name of the source.
                - url (str): The full API endpoint URL.
                - json_path (str): The JSON path to the price value in the API response.
                - inverse (Optional[bool]): Whether to invert the rate (1/price). Defaults to False.
            quote_required Optional[bool]: Whether to use the quote currency for rate calculations.
        """
        super().__init__(
            asset_a, asset_b, pair_type, sources, quote_required, quote_calc_method
        )

    async def get_rates(self) -> Optional[dict[str, Any]]:
        """Fetches rate information from the API sources based on the asset pair.

        Returns:
            Optional[dict[str, Any]]: The rate information or None if an error occurs.
        """
        rates = []
        logger.info(
            "------------------------------------------------------------------"
        )
        logger.info(
            f"--------------- GenericApi - {self.asset_a} - {self.asset_b} ---------------"
        )
        logger.info(
            "------------------------------------------------------------------"
        )
        async with aiohttp.ClientSession() as session:
            tasks = [self._fetch_rate(source, session) for source in self.sources]
            results = await asyncio.gather(*tasks)

            rates = [result for result in results if result is not None]

        logger.info(
            "----------------------------------------------------------------------------------"
        )
        if rates:
            return {
                "asset_a_name": self.asset_a.upper(),
                "asset_b_name": self.asset_b.upper(),
                "rates": rates,
            }
        else:
            logger.warning(f"No valid rates found for {self.asset_a}-{self.asset_b}")
            return None

    async def _fetch_rate(
        self, source: dict, session: aiohttp.ClientSession
    ) -> Optional[dict[str, Any]]:
        """Fetches the rate for a single source."""
        name = source.get("name")
        url = source.get("api_url")
        json_path = source.get("json_path")
        inverse = source.get("inverse", False)

        try:
            async with session.get(
                url, headers=self._build_headers(source)
            ) as response:
                if response.status != 200:
                    logger.warning(
                        f"Failed to fetch data from {name}: HTTP {response.status}"
                    )
                    return None

                data = await response.json()
                price = self._get_json_value(data, json_path)

                if price is None:
                    logger.warning(
                        f"Failed to extract price from {name}: Invalid JSON path {json_path}"
                    )
                    return None

                if inverse:
                    price = 1 / float(price)

                logger.info(f"{name} - {price} - API_URL: {url}")
                return {
                    "source": name,
                    "price": float(price),
                    "source_id": super().get_source_id(name),
                }
        except Exception as error:
            logger.error(f"Error fetching rate from {name}: {error}")
            return None

    def get_asset_names(self) -> Tuple[str, str]:
        """Returns the asset pair names for the adapter, in uppercase."""
        return self.asset_a.upper(), self.asset_b.upper()

    def _get_json_value(
        self, data: Any, json_path: list[Union[str, int]]
    ) -> Optional[float]:
        try:
            for key in json_path:
                if isinstance(key, int) and isinstance(data, list):
                    data = data[key]
                elif isinstance(key, str) and isinstance(data, dict):
                    data = data[key]
                else:
                    return None
            return float(data) if isinstance(data, (int, float, str)) else None
        except (IndexError, KeyError, ValueError, TypeError) as error:
            logger.error(f"Error extracting JSON value at path {json_path}: {error}")
            return None

    def _build_headers(self, source: dict[str, Any]) -> dict[str, str]:
        """
        Builds the headers for the API request based on the provided source information.

        Args:
            source (dict[str, Any]): The source configuration including any headers or tokens.

        Returns:
            dict[str, str]: The headers for the API request.
        """
        headers = {}

        if "headers" in source and isinstance(source["headers"], dict):
            source_headers = source["headers"]

            if "bearer_token" in source_headers:
                headers["Authorization"] = f"Bearer {source_headers['bearer_token']}"

            for key, value in source_headers.items():
                if key != "bearer_token":
                    headers[key] = value

        return headers

    def get_sources(self) -> list[dict[str, Any]]:
        """Returns the asset pair names for the adapter."""
        return self.sources

    def _log_sources_summary(self) -> str:
        """Provides a summary of sources specific to GenericApiAdapter."""
        logger.info("SOURCES:")
        for source in self.sources:
            logger.info(
                "  - NAME: %s, INVERSE: %s",
                source.get("name"),
                "Yes" if source.get("inverse", False) else "No",
            )
