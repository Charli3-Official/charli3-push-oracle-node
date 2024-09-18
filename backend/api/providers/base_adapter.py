import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

logger = logging.getLogger(__name__)


class BaseAdapter(ABC):
    """
    Base class for an adapter to fetch rates for an asset pair.
    """

    def __init__(
        self,
        asset_a: str,
        asset_b: str,
        pair_type: str,
        sources: Optional[list[str] | list[dict[str, Any]]] = None,
        quote_required: Optional[bool] = False,
        quote_calc_method: Optional[str] = None,
    ) -> None:
        """Constructor for the AbstractAdapter class.
        Args:
            asset_a (str): The name of asset A (base token).
            asset_b (str): The name of asset B (quote token).
            quote (bool): Whether to use quote currency for rate calculations.
        """
        self.asset_a = asset_a
        self.asset_b = asset_b
        self.pair_type = pair_type
        self.sources = sources
        self.quote_required = quote_required
        self.quote_calc_method = quote_calc_method
        self.source_ids = {}

    def get_type(self) -> str:
        """Returns the type of adapter."""
        return self.pair_type

    def get_quote_required(self) -> bool:
        """Returns whether the adapter requires a quote currency for rate calculations."""
        return self.quote_required

    def get_quote_calc_method(self) -> str:
        """Returns the method used to calculate the quote currency."""
        return self.quote_calc_method if self.quote_calc_method else "multiply"

    def set_source_id(self, source_name: str, source_id: int):
        """Set the provider ID for a given source."""
        self.source_ids[source_name] = source_id

    def get_source_id(self, source_name: str) -> Optional[str]:
        """Get the provider ID for a given source."""
        return self.source_ids.get(source_name)

    @abstractmethod
    async def get_rates(self) -> Optional[dict[str, any]]:
        """Fetches rate information for the asset pair."""
        pass

    @abstractmethod
    def get_asset_names(self) -> tuple[str, str]:
        """Returns the asset pair names for the adapter."""
        pass

    @abstractmethod
    def get_sources(self) -> list[str] | list[dict[str, Any]]:
        """Returns the source names registered for the adapter."""
        pass

    def _log_sources_summary(self) -> None:
        """Helper method to provide a summary of sources. This should be overridden by subclasses."""
        raise NotImplementedError("Subclasses should implement this method.")

    def log_summary(self):
        """Logs a summary of the adapter configuration."""
        asset_a_name, asset_b_name = self.get_asset_names()
        logger.info("----------------------------------------------------")
        logger.info("--------- ADAPTER CONFIGURATION SUMMARY ---------")
        logger.info("ADAPTER NAME: %s", self.__class__.__name__)
        logger.info("ASSET: %s - %s", asset_a_name, asset_b_name)
        logger.info("TYPE: %s", self.pair_type)
        logger.info("# OF SOURCES: %s", len(self.sources))
        logger.info("-----------------------------------------------")
        logger.info("QUOTE REQUIRED: %s", "Yes" if self.quote_required else "No")
        logger.info("-----------------------------------------------")
        self._log_sources_summary()
        logger.info("-----------------------------------------------")
