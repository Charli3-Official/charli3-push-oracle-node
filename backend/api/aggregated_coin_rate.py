"""Aggregated Coin Rate module."""

import asyncio
import json
import logging
from datetime import datetime
from statistics import median
from typing import Any, Optional, Tuple
from urllib.parse import urlparse

from charli3_offchain_core.chain_query import ChainQuery
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.providers import BaseAdapter, Charli3DendriteAdapter, GenericApiAdapter
from backend.db.database import get_session

from ..db.crud.providers_crud import Provider, ProviderCreate, providers_crud
from ..db.service import store_aggregated_rate_details, store_rate_dataflow

logger = logging.getLogger(__name__)


class AggregatedCoinRate:
    """Handles rate review on market"""

    def __init__(
        self,
        quote_currency: bool = False,
        quote_symbol: Optional[str] = None,
        chain_query: ChainQuery = None,
        feed_id: Optional[str] = None,
        slack_alerts: Optional[dict[str, str]] = None,
    ):
        self.quote_currency = quote_currency
        self.quote_symbol = quote_symbol
        self.base_data_adapters: Optional[list[BaseAdapter]] = []
        self.quote_data_adapters: Optional[list[BaseAdapter]] = []
        self.chain_query = chain_query
        self.feed_id = feed_id
        self.slack_alerts = slack_alerts or {}

    async def _ensure_provider_in_db(
        self,
        provider_name: str,
        feed_type: str,
        db_session: AsyncSession,
        symbol: str,
        api_url: Optional[str] = None,
    ) -> Provider:
        """
        Ensures that a provider is present in the database, updating or creating it as necessary.
        """
        # Attempt to fetch the provider by name and feed_id
        existing_provider = await providers_crud.get_provider_by_name_and_feed_id(
            name=provider_name,
            feed_id=self.feed_id,
            adapter_type=feed_type,
            db_session=db_session,
        )
        if not existing_provider:
            # logger.info("Provider %s not found in the database", provider_name)
            # If the provider doesn't exist, create a new one
            base_url, path = self.parse_api_url(api_url)

            provider_data = ProviderCreate(
                name=provider_name,
                feed_id=self.feed_id,
                adapter_type=feed_type,
                token=symbol,
                api_url=base_url,
                path=path,
            )
            # logger.info("Creating provider %s in the database", provider_name)
            return await providers_crud.create(
                obj_in=provider_data, db_session=db_session
            )
        # logger.info("Provider %s exists in the database", provider_name)
        return existing_provider

    async def add_providers(
        self, config: dict, db_session, pair_type: str
    ) -> Tuple[list[BaseAdapter], list[Provider]]:
        """
        Set providers from the provided configuration list.

        Args:
            config (Dict): Configuration for either base or quote providers.
            db_session (AsyncSession): Database session.
            pair_type (str): Can be "base" or "quote" to specify the type of adapter.
        """
        dex_configs = config.get("dexes", [])
        api_configs = config.get("api_sources", [])
        db_providers = []

        # Initialize provider storage based on type (base or quote)
        if pair_type == "base":
            providers = self.base_data_adapters
        else:
            providers = self.quote_data_adapters

        # Handle multiple Charli3DendriteAdapter instances
        for dex_config in dex_configs:
            if dex_config.get("adapter") == "charli3-dendrite":
                dendrite_adapter = Charli3DendriteAdapter(
                    asset_a=dex_config.get("asset_a", "lovelace"),
                    asset_b=dex_config.get("asset_b", "lovelace"),
                    sources=dex_config.get("sources", []),
                    pair_type=pair_type,
                    quote_required=dex_config.get("quote_required", False),
                    quote_calc_method=dex_config.get("quote_calc_method", None),
                )

                # Ensure any new providers that have been added in the config are saved to the database.
                asset_a_name, asset_b_name = dendrite_adapter.get_asset_names()
                for source in dendrite_adapter.get_sources():
                    db_provider = await self._ensure_provider_in_db(
                        provider_name=source,
                        feed_type=f"charli3-dendrite-{pair_type}",
                        db_session=db_session,
                        symbol=f"{asset_a_name}-{asset_b_name}",
                    )
                    dendrite_adapter.set_source_id(source, str(db_provider.id))

                # Append the initialized adapter to the respective provider list
                providers.append(dendrite_adapter)
                db_providers.extend(self.get_providers_from_adapter(dendrite_adapter))

        # Handle multiple GenericApiAdapter instances
        for api_config in api_configs:
            if api_config.get("adapter") == "generic-api":
                api_sources = []
                for source in api_config.get("sources", []):
                    api_sources.append(
                        {
                            "name": source.get("name"),
                            "api_url": source.get("api_url"),
                            "json_path": source.get("json_path"),
                            "headers": source.get("headers", {}),
                            "inverse": source.get("inverse", False),
                        }
                    )

                generic_adapter = GenericApiAdapter(
                    asset_a=api_config.get("asset_a", "lovelace"),
                    asset_b=api_config.get("asset_b", "lovelace"),
                    pair_type=pair_type,
                    sources=api_sources,
                    quote_required=api_config.get("quote_required", False),
                    quote_calc_method=api_config.get("quote_calc_method", None),
                )

                asset_a_generic, asset_b_generic = generic_adapter.get_asset_names()
                for source in generic_adapter.get_sources():
                    db_provider = await self._ensure_provider_in_db(
                        provider_name=source.get("name"),
                        feed_type=f"generic-api-{pair_type}",
                        db_session=db_session,
                        symbol=f"{asset_a_generic}-{asset_b_generic}",
                        api_url=source.get("api_url"),
                    )
                    generic_adapter.set_source_id(
                        source.get("name"), str(db_provider.id)
                    )

                providers.append(generic_adapter)
                db_providers.extend(self.get_providers_from_adapter(generic_adapter))

        return providers, db_providers

    async def get_rate_from_providers(
        self,
        adapters: list[BaseAdapter],
        quote_rate: Optional[float] = None,
        conversion_symbol=None,
    ) -> Tuple[Optional[float], list[dict[str, Any]]]:
        """Get rate from providers (adapters), handle those requiring quote calculation.

        Args:
            adapters (list[AbstractAdapter]): list of adapters to fetch rates from.
            quote_rate (Optional[float], optional): quote rate. Defaults to None.
            conversion_symbol (str, optional): Symbol for conversion. Defaults to None.

        Returns:
            Tuple[Optional[float], list[dict[str, Any]]]: aggregated rate and provider responses.
        """
        request_time = datetime.utcnow()
        # rates_to_get = [adapter.get_rates() for adapter in adapters]

        # # Fetch all the rates concurrently
        # responses = await asyncio.gather(*rates_to_get, return_exceptions=True)

        responses = []
        for adapter in adapters:
            try:
                response = await adapter.get_rates()
                responses.append(response)
            except Exception as error:
                # Handle exceptions as needed
                responses.append(error)

        provider_responses = []
        valid_rates = []
        no_response_providers = []
        invalid_providers = []
        valid_providers = []

        # Process each response and handle those with quote_required = True
        for response, adapter in zip(responses, adapters):
            # Initialize a dictionary to hold response details for logging
            asset_a_name, asset_b_name = adapter.get_asset_names()

            if isinstance(response, dict) and "rates" in response:
                # Process valid responses with rates
                for rate_info in response["rates"]:
                    rate = rate_info.get("price")

                    # If the adapter requires quote conversion, apply quote_rate multiplication
                    if adapter.quote_required and quote_rate is not None:
                        calc_method = adapter.get_quote_calc_method()
                        if calc_method.lower() == "multiply":
                            rate = float(rate) * float(quote_rate)
                        elif calc_method.lower() == "divide":
                            rate = float(rate) / float(quote_rate)
                        logger.info(
                            f"Conversion: {rate_info.get('source')}- Method: {calc_method} - Rate: {rate} from {rate_info.get('price')}"
                        )

                    provider_response = {
                        "provider_id": rate_info.get("source_id"),
                        "feed_id": self.feed_id,
                        "rate": rate,
                        "request_timestamp": request_time,
                        "symbol": f"{asset_a_name}-{asset_b_name}",
                        "path": rate_info.get("source"),
                        "response_code": 200,
                        "response_body": json.dumps(rate_info),
                        "rate_type": adapter.pair_type,
                    }

                    provider_responses.append(provider_response)

                    if rate is not None and isinstance(rate, (int, float)) and rate > 0:
                        valid_rates.append(rate)
                        valid_providers.append(rate_info.get("source"))
                    else:
                        invalid_providers.append(rate_info.get("source"))

        # Ensure that all adapters with quote_required=True were processed
        if quote_rate is None and any(adapter.quote_required for adapter in adapters):
            logger.error(
                "Some adapters require a quote rate, but no quote rate was provided."
            )
            return None, provider_responses

        # If no valid rates are found, return None
        if not valid_rates:
            logger.critical("No data prices are available to estimate the median")
            return None, provider_responses

        # Calculate the aggregated rate (median of valid rates)
        aggregated_rate = median(valid_rates)
        logger.info(
            "----------------------------------------------------------------------"
        )
        logger.info(
            "Aggregated rate calculated: %s from %s", aggregated_rate, valid_rates
        )
        logger.info(
            "----------------------------------------------------------------------"
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

        # Fetch Median Quote Rate first if quote_currency is True
        if self.quote_currency:
            logger.info(
                "------------------------------------------------------------------"
            )
            logger.info(
                "---------------------FETCHING QUOTE RATES--------------------------"
            )
            quote_rate, quote_provider_responses = await self.get_rate_from_providers(
                adapters=self.quote_data_adapters
            )

            logger.info("Quote Rate: %s", quote_rate)
            if quote_rate is None:
                logger.error("No valid quote rates available.")
        logger.info(
            "------------------------------------------------------------------"
        )
        logger.info(
            "------------------FETCHING BASE RATES-----------------------------"
        )
        # Fetch Median Base Rate with quote_rate calculation if quote_currency is enabled
        base_rate, base_provider_responses = await self.get_rate_from_providers(
            self.base_data_adapters, quote_rate, self.quote_symbol
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

    def get_providers_from_adapter(self, adapter: BaseAdapter) -> list[Provider]:
        """Get all providers from the adapter."""
        providers = []
        asset_a_name, asset_b_name = adapter.get_asset_names()
        sources = adapter.get_sources()

        for source in sources:
            if isinstance(adapter, Charli3DendriteAdapter):
                provider = Provider(
                    id=adapter.get_source_id(source),
                    name=source,
                    feed_id=self.feed_id,
                    adapter_type=f"charli3-dendrite-{adapter.pair_type}",
                    token=f"{asset_a_name}-{asset_b_name}",
                    api_url="",
                    path="",
                )
            elif isinstance(adapter, GenericApiAdapter):
                base_url, path = self.parse_api_url(source.get("api_url", ""))
                provider = Provider(
                    id=adapter.get_source_id(source.get("name")),
                    name=source.get("name"),
                    feed_id=self.feed_id,
                    adapter_type=f"generic-api-{adapter.pair_type}",
                    token=f"{asset_a_name}-{asset_b_name}",
                    api_url=base_url,
                    path=path,
                )
            else:
                continue
            providers.append(provider)

        return providers

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

    def parse_api_url(self, api_url: str) -> tuple[str, str]:
        """Parses the given API URL and returns the base URL and path."""
        if api_url:
            parsed_url = urlparse(api_url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            path = (
                f"{parsed_url.path}?{parsed_url.query}"
                if parsed_url.query
                else parsed_url.path
            )
        else:
            base_url = ""
            path = ""
        return base_url, path
