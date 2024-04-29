"""Aggregated Coin Rate module."""

from typing import Optional, List, Any, Dict, Tuple
from datetime import datetime
import logging
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from charli3_offchain_core.consensus import random_median
from charli3_offchain_core.chain_query import ChainQuery

from backend.db.database import get_session
from backend.api.providers import (
    CoinRate,
    Generic,
    BinanceApi,
    CoingeckoApi,
    SundaeswapApi,
    MinswapApi,
    WingridersApi,
    MuesliswapApi,
    VyFiApi,
    InverseCurrencyRate,
    Charli3Api,
)
from ..db.crud.providers_crud import providers_crud, ProviderCreate, Provider
from ..db.service import store_aggregated_rate_details, store_rate_dataflow

apiTypes = {
    "generic": Generic,
    "binance": BinanceApi,
    "coingecko": CoingeckoApi,
    "sundaeswap": SundaeswapApi,
    "minswap": MinswapApi,
    "wingriders": WingridersApi,
    "muesliswap": MuesliswapApi,
    "vyfi": VyFiApi,
    "inverserate": InverseCurrencyRate,
    "charli3": Charli3Api,
}

logger = logging.getLogger(__name__)


class AggregatedCoinRate:
    """Handles rate review on market"""

    def __init__(
        self,
        quote_currency: bool = False,
        quote_symbol: Optional[str] = None,
        chain_query: ChainQuery = None,
        feed_id: Optional[str] = None,
    ):
        self.quote_currency = quote_currency
        self.quote_symbol = quote_symbol
        self.base_data_providers: List[CoinRate] = []
        self.quote_data_providers: List[CoinRate] = []
        self.chain_query = chain_query
        self.feed_id = feed_id

    async def _ensure_provider_in_db(
        self,
        provider_name: str,
        feed_type: str,
        db_session: AsyncSession,
        **pair: Any,
    ) -> Provider:
        """
        Ensures that a provider is present in the database, updating or creating it as necessary.
        """
        # Attempt to fetch the provider by name and feed_id
        existing_provider = await providers_crud.get_provider_by_name_and_feed_id(
            name=provider_name, feed_id=self.feed_id, db_session=db_session
        )

        if not existing_provider:
            symbol = pair.get("symbol")
            # If the provider doesn't exist, create a new one
            provider_data = ProviderCreate(
                name=provider_name,
                feed_id=self.feed_id,
                adapter_type=feed_type,
                token=symbol,
                api_url=pair.get("api_url", ""),
                path=pair.get("path", ""),
            )
            return await providers_crud.create(
                obj_in=provider_data, db_session=db_session
            )
        return existing_provider

    async def add_base_data_provider(
        self, feed_type, provider, pair, db_session
    ) -> Provider:
        """add provider to list."""
        provider = await self._ensure_provider_in_db(
            provider_name=provider,
            feed_type=feed_type,
            feed_id=self.feed_id,
            db_session=db_session,
            **pair,
        )
        if provider and hasattr(provider, "id"):
            provider_instance = apiTypes[feed_type](
                provider, provider_id=provider.id, **pair
            )
            self.base_data_providers.append(provider_instance)
        return provider

    async def add_quote_data_provider(
        self, feed_type, provider, pair, db_session
    ) -> Provider:
        """add provider to list."""
        provider = await self._ensure_provider_in_db(
            provider_name=provider,
            feed_type=feed_type,
            feed_id=self.feed_id,
            db_session=db_session,
            **pair,
        )
        if provider and hasattr(provider, "id"):
            provider_instance = apiTypes[feed_type](
                provider, provider_id=provider.id, **pair
            )
            self.quote_data_providers.append(provider_instance)
        return provider

    async def get_rate_from_providers(
        self,
        providers: List[CoinRate],
        quote_rate: Optional[float] = None,
        conversion_symbol=None,
    ) -> Tuple[Optional[float], List[Dict[str, Any]]]:
        """Get rate from providers.

        Args:
            providers (List[CoinRate]): list of providers
            quote_rate (Optional[float], optional): quote rate. Defaults to None.

        Returns:
            Tuple[Optional[float], List[Dict[str, Any]]]: aggregated rate and provider responses
        """
        request_time = datetime.utcnow()
        rates_to_get = []
        for provider in providers:
            rates_to_get.append(
                provider.get_rate(self.chain_query, quote_rate, conversion_symbol)
            )

        responses = await asyncio.gather(*rates_to_get, return_exceptions=True)

        provider_responses = []
        valid_rates = []

        for response, provider in zip(responses, providers):
            provider_response = {
                "provider_id": response.get("provider_id"),
                "feed_id": self.feed_id,
                "request_timestamp": request_time,
                "symbol": response.get("symbol"),
                "rate": (
                    None if isinstance(response, Exception) else response.get("rate")
                ),
                "path": (
                    None if isinstance(response, Exception) else response.get("path")
                ),
                "response_code": (
                    None
                    if isinstance(response, Exception)
                    else response.get("response_code")
                ),
                "response_body": (
                    str(response)
                    if isinstance(response, Exception)
                    else response.get("response_body")
                ),
                "rate_type": (
                    None
                    if isinstance(response, Exception)
                    else response.get("rate_type")
                ),
            }
            provider_responses.append(provider_response)

            if (
                not isinstance(response, Exception)
                and response.get("rate") is not None
                and isinstance(response.get("rate"), (int, float))
                and response.get("rate") > 0
            ):
                valid_rates.append(response.get("rate"))

        if not valid_rates:
            logger.critical("No data prices are available to estimate the median")
            return None, provider_responses

        aggregated_rate = random_median(valid_rates)
        logger.info(
            "Aggregated rate calculated : %s from %s", aggregated_rate, valid_rates
        )
        return aggregated_rate, provider_responses

    async def get_aggregated_rate(self) -> Tuple[Optional[float], Optional[str]]:
        """calculate aggregated rate from list of data providers.

        Returns:
            Tuple[Optional[float], Optional[str]]: aggregated rate and aggregation id
        """
        request_time = datetime.utcnow()
        quote_rate = None
        quote_provider_responses = []
        aggregation_id = None  # Default value
        logger.info("get_aggregated_rate: fetching price from data providers")

        # Fetch Median Quote Rate first if quote_currency is True
        if self.quote_currency:
            logger.info("fetching quote price from data providers")
            quote_rate, quote_provider_responses = await self.get_rate_from_providers(
                self.quote_data_providers
            )
            if quote_rate is None:
                logger.error("No valid quote rates available.")

        # Fetch Median Base Rate with quote_rate calculation if quote_currency is enabled
        base_rate, base_provider_responses = await self.get_rate_from_providers(
            self.base_data_providers, quote_rate, self.quote_symbol
        )

        if base_rate is None:
            logger.error("No valid base rates available.")
            return None, None

        # Save the aggregated rate first
        try:
            async with get_session() as db_session:
                aggregated_rate_details = await store_aggregated_rate_details(
                    db_session, base_rate, self.feed_id, request_time
                )
                aggregation_id = aggregated_rate_details.id

                # Update provider responses with aggregation_id and save them
                all_provider_responses = (
                    quote_provider_responses + base_provider_responses
                )
                for response in all_provider_responses:
                    response["rate_aggregation_id"] = aggregation_id
                await store_rate_dataflow(db_session, all_provider_responses)

        except Exception as db_error:
            logger.error("Error saving aggregated rate details: %s", db_error)
            return base_rate, aggregation_id

        return base_rate, aggregation_id
