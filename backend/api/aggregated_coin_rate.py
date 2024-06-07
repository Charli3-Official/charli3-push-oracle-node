"""Aggregated Coin Rate module."""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from charli3_offchain_core.chain_query import ChainQuery
from charli3_offchain_core.consensus import random_median
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.providers import (
    BinanceApi,
    Charli3Api,
    CoingeckoApi,
    CoinRate,
    Generic,
    InverseCurrencyRate,
    MinswapApi,
    MuesliswapApi,
    SundaeswapApi,
    VyFiApi,
    WingridersApi,
)
from backend.db.database import get_session

from ..db.crud.providers_crud import Provider, ProviderCreate, providers_crud
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
        slack_alerts: Optional[Dict[str, str]] = None,
    ):
        self.quote_currency = quote_currency
        self.quote_symbol = quote_symbol
        self.base_data_providers: List[CoinRate] = []
        self.quote_data_providers: List[CoinRate] = []
        self.chain_query = chain_query
        self.feed_id = feed_id
        self.slack_alerts = slack_alerts or {}

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
                provider, provider_id=provider.id, rate_type="base", **pair
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
                provider, provider_id=provider.id, rate_type="quote", **pair
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
        no_response_providers = []
        invalid_providers = []
        valid_providers = []

        for response, provider in zip(responses, providers):
            # Initialize a dictionary to hold response details
            provider_response = {
                "provider_id": None,
                "feed_id": self.feed_id,
                "request_timestamp": request_time,
                "symbol": None,
                "rate": None,
                "path": None,
                "response_code": None,
                "response_body": None,
                "rate_type": None,
            }

            if isinstance(response, Exception):
                # Log the error but do not process further
                logger.error(
                    "Error fetching data from provider %s: %s", provider, response
                )

                no_response_providers.append(provider.provider.name)
            elif isinstance(response, dict) and response.get("provider_id"):
                # Process only if response is a dictionary and provider_id is present
                provider_response.update(
                    {
                        "provider_id": response.get("provider_id"),
                        "symbol": response.get("symbol"),
                        "rate": response.get("rate"),
                        "path": response.get("path"),
                        "response_code": response.get("response_code"),
                        "response_body": response.get("response_body"),
                        "rate_type": response.get("rate_type"),
                    }
                )
                # Append the response to the list of provider responses
                provider_responses.append(provider_response)
                rate = response.get("rate")
                if rate is not None and isinstance(rate, (int, float)) and rate > 0:
                    valid_rates.append(rate)
                    valid_providers.append(provider.provider.name)
                else:
                    invalid_providers.append(provider.provider.name)
            else:
                logger.warning(
                    "Invalid response from provider %s: %s", provider, response
                )
                no_response_providers.append(provider.provider.name)

        # Slack Alert system
        minimum_data_sources = int(self.slack_alerts.get("minimum_data_sources", 2))
        if len(valid_rates) <= minimum_data_sources:
            valid_provider_names = valid_providers
            no_response_provider_names = no_response_providers
            invalid_data_provider_names = invalid_providers
            alert_message = (
                f"*Insufficient Data Sources*: Valid [{len(valid_rates)}], Minimum Required [{minimum_data_sources}], Total Configured [{len(responses)}]\n"
                f"*Valid Data Sources*: {valid_provider_names if valid_provider_names else 'None'} ({len(valid_provider_names)})\n"
                f"*No Response (exceptions)*: {no_response_provider_names if no_response_provider_names else 'None'} ({len(no_response_provider_names)})\n"
                f"*Invalid Data Source*: {invalid_data_provider_names if invalid_data_provider_names else 'None'} ({len(invalid_data_provider_names)})\n"
                f"*Feed ID*: {self.feed_id}\n"
            )
            self.send_slack_alert(alert_message)

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

    def send_slack_alert(self, message: str):
        slack_token = self.slack_alerts.get("token")
        slack_channel = self.slack_alerts.get("channel")

        if slack_token and slack_channel:
            logger.critical(message)
            slack_client = WebClient(token=slack_token)
            try:
                slack_client.chat_postMessage(channel=slack_channel, text=message)
            except SlackApiError as e:
                logger.error(f"Slack API error: {e.response['error']}")
        else:
            logger.warning("Slack alert configuration is missing or incomplete.")
