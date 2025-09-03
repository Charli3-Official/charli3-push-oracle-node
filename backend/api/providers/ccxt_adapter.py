import asyncio
import logging
import time
from typing import Any, Optional

import ccxt.async_support as ccxt

from .base_adapter import BaseAdapter

logger = logging.getLogger(__name__)


class CCXTAdapter(BaseAdapter):
    """
    Adapter for fetching rates using CCXT from centralized exchanges.
    """

    def __init__(
        self,
        asset_a: str,
        asset_b: str,
        pair_type: str,
        sources: Optional[list[str] | list[dict[str, Any]]] = None,
        quote_required: Optional[bool] = False,
        quote_calc_method: Optional[str] = None,
        concurrent_requests: int = 20,
    ) -> None:
        super().__init__(
            asset_a, asset_b, pair_type, sources, quote_required, quote_calc_method
        )
        self._exchanges: dict[str, ccxt.Exchange] = {}
        self._semaphore = asyncio.Semaphore(concurrent_requests)
        self._setup_exchanges()

    def _setup_exchanges(self) -> None:
        """Initialize CCXT exchange instances."""
        for source in self.sources or []:
            name = (
                source["name"].lower()
                if isinstance(source, dict) and "name" in source
                else str(source).lower()
            )
            if not hasattr(ccxt, name):
                logger.warning(f"Exchange {name} not supported by CCXT")
                continue
            try:
                config = {
                    "enableRateLimit": True,
                    "timeout": 10000,
                }

                if name == "htx":
                    config["verify"] = False

                if isinstance(source, dict):
                    if "api_key" in source and "secret" in source:
                        config.update(
                            {"apiKey": source["api_key"], "secret": source["secret"]}
                        )
                exchange_class = getattr(ccxt, name)
                self._exchanges[name] = exchange_class(config)
            except Exception as e:
                logger.error(f"Failed to initialize {name}: {str(e)}")

    def get_asset_names(self) -> tuple[str, str]:
        return self.asset_a, self.asset_b

    def get_sources(self) -> list[str] | list[dict[str, Any]]:
        return self.sources or []

    def _log_sources_summary(self) -> None:
        """Log a summary of the configured exchanges."""
        sources = self.get_sources()
        logger.info("EXCHANGES: %s", ", ".join(str(s) for s in sources))

    async def get_rates(self) -> Optional[dict[str, Any]]:
        """Fetch rates from configured exchanges."""
        tasks = []
        for exchange_id, exchange in self._exchanges.items():
            tasks.append(self._get_exchange_rate(exchange_id, exchange))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        rates_list = []
        for idx, result in enumerate(results):
            exchange_id = list(self._exchanges.keys())[idx]
            if isinstance(result, Exception):
                logger.error(f"Rate fetch error for {exchange_id}: {str(result)}")
                continue
            if result is not None:
                rate_info = {
                    "source": exchange_id,
                    "source_id": self.get_source_id(exchange_id),
                    "price": result["price"],
                    "bid": result.get("bid"),
                    "ask": result.get("ask"),
                    "volume": result.get("baseVolume"),
                    "timestamp": result["timestamp"],
                }
                logger.info(
                    f"Exchange {exchange_id}: price={result['price']}, bid={result.get('bid')}, ask={result.get('ask')}, volume={result.get('baseVolume')}"
                )
                rates_list.append(rate_info)
        return {"rates": rates_list} if rates_list else None

    async def _get_exchange_rate(
        self, exchange_id: str, exchange: ccxt.Exchange
    ) -> Optional[dict[str, Any]]:
        """Get rate from a single exchange."""
        try:
            async with self._semaphore:
                symbol = f"{self.asset_a}/{self.asset_b}"
                if not exchange.markets:
                    await exchange.load_markets()
                if symbol not in exchange.markets:
                    logger.warning(f"{symbol} not available on {exchange_id}")
                    return None
                ticker = await exchange.fetch_ticker(symbol)
                if not ticker or ticker.get("last") is None:
                    return None
                return {
                    "price": float(ticker["last"]),
                    "bid": ticker.get("bid"),
                    "ask": ticker.get("ask"),
                    "volume": ticker.get("baseVolume"),
                    "timestamp": ticker.get("timestamp", time.time() * 1000) / 1000,
                }
        except Exception as e:
            logger.error(f"Error fetching from {exchange_id}: {str(e)}")
            return None
        finally:
            try:
                await exchange.close()
            except Exception:
                pass

    async def close(self) -> None:
        """Close all exchange connections."""
        for exchange in self._exchanges.values():
            try:
                await exchange.close()
            except Exception:
                pass
