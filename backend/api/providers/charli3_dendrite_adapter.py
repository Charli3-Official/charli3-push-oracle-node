import asyncio
import logging
from decimal import Decimal
from typing import Any, Optional, Tuple

from charli3_dendrite import (
    MinswapCPPState,
    MinswapV2CPPState,
    MuesliSwapCPPState,
    SpectrumCPPState,
    SplashCPPState,
    SundaeSwapCPPState,
    SundaeSwapV3CPPState,
    VyFiCPPState,
    WingRidersCPPState,
    WingRidersV2CPPState,
)
from charli3_dendrite.backend import get_backend
from charli3_dendrite.dexs.amm.amm_base import AbstractPoolState
from charli3_dendrite.dexs.core.errors import (
    InvalidLPError,
    InvalidPoolError,
    NoAssetsError,
)

from backend.api.providers.base_adapter import BaseAdapter

logger = logging.getLogger(__name__)

SUPPORTED_DEXES: list[AbstractPoolState] = {
    "sundaeswapv3": SundaeSwapV3CPPState,
    "sundaeswap": SundaeSwapCPPState,
    "splash": SplashCPPState,
    "spectrum": SpectrumCPPState,
    "minswap": MinswapCPPState,
    "minswapv2": MinswapV2CPPState,
    "wingriders": WingRidersCPPState,
    "wingridersv2": WingRidersV2CPPState,
    "muesliswap": MuesliSwapCPPState,
    "vyfi": VyFiCPPState,
}

SCRIPT_HASH_SIZE = 28


class Charli3DendriteAdapter(BaseAdapter):
    """
    Dendrite adapter to handle fetching rates for a token pair across multiple DEXs.
    This class abstracts DEX interaction using the charli3-dendrite package.
    """

    def __init__(
        self,
        asset_a: str,
        asset_b: str,
        pair_type: str,
        sources: Optional[list[str]] = None,
        quote_required: Optional[bool] = False,
        quote_calc_method: Optional[str] = None,
    ) -> None:
        """Constructor for the DendriteAdapter class.
        Args:
            asset_a (str): The name of asset A (base token).
            asset_b (str): The name of asset B (quote token).
            pair_type (str): Type of asset pair i.e base or quote.
            sources (Optional[list[str]]): a list of DEX names selected.
            quote_required: Optional[bool]: Whether to use the quote currency for rate calculations.
            quote_calc_method: Optional[str]: The method used to calculate the quote currency. Defaults to 'multiply'.
        """
        if sources is None:
            sources = list(SUPPORTED_DEXES.keys())
        else:
            for dex in sources:
                if dex not in SUPPORTED_DEXES:
                    raise ValueError(f"Unsupported DEX sources: {dex}")

        super().__init__(
            asset_a, asset_b, pair_type, sources, quote_required, quote_calc_method
        )

    async def get_rates(self) -> Optional[dict[str, Any]]:
        """Fetches rate information from the DEXs based on the sources pool IDs and asset pair.

        Returns:
            Optional[Dict[str, Any]]: The rate information or None if an error occurs.
        """

        asset_a_name, asset_b_name = self.get_asset_names()
        rates = []
        logger.info(
            "------------------------------------------------------------------"
        )
        logger.info(
            "--------------- Charli3-Dendrite - %s - %s ---------------",
            asset_a_name,
            asset_b_name,
        )
        logger.info(
            "------------------------------------------------------------------"
        )
        try:
            batch_requests = [
                Charli3DendriteAdapter.fetch_dex_rate(name, self.asset_a, self.asset_b)
                for name in self.sources
            ]
            results = await asyncio.gather(*batch_requests)
            for name, result in zip(self.sources, results):
                if result:
                    rates.append(
                        {
                            "source": name,
                            "price": result,
                            "source_id": super().get_source_id(name),
                        }
                    )
        except Exception as error:
            logger.error("Critical error in get_rates: %s", error)
            return None

        if rates:
            return {
                "asset_a_name": asset_a_name,
                "asset_b_name": asset_b_name,
                "rates": rates,
            }
        logger.warning("No matching pool found for %s-%s", asset_a_name, asset_b_name)
        return None

    def get_asset_names(self) -> Tuple[str, str]:
        """Returns the asset pair names for the adapter with a fallback to CIP-68 decoding."""

        def decode_asset(asset_hex: str) -> str:
            """Attempts to decode an asset name and falls back to CIP-68 decoding if necessary."""
            try:
                return bytes.fromhex(asset_hex[SCRIPT_HASH_SIZE * 2 :]).decode(
                    encoding="utf-8"
                )
            except UnicodeDecodeError:
                return self.remove_label_and_decode(asset_hex[SCRIPT_HASH_SIZE * 2 :])

        asset_a_name = (
            "ADA" if self.asset_a == "lovelace" else decode_asset(self.asset_a)
        )
        asset_b_name = (
            "ADA" if self.asset_b == "lovelace" else decode_asset(self.asset_b)
        )

        return asset_a_name, asset_b_name

    def get_sources(self) -> list[str]:
        """Returns the dexes sources names registered for the adapter."""
        return self.sources

    @staticmethod
    def get_correct_price(pool: Any, assets: list[str]) -> Optional[Decimal]:
        """
        Private function to get the correct price based on the asset pair.

        Args:
            validated_pool (Any): The validated pool object containing assets and prices.

        Returns:
            Optional[Decimal]: The correct price (A to B or B to A) or None if not found.
        """
        try:
            pool_assets = pool.assets.model_dump()
            price_a_to_b, price_b_to_a = pool.price

            asset_a = list(pool_assets.keys())[0]
            asset_b = list(pool_assets.keys())[1]

            if assets[0] in asset_a and assets[1] in asset_b:
                return price_b_to_a

            if assets[0] in asset_b and assets[1] in asset_a:
                return price_a_to_b

            return None

        except (NoAssetsError, InvalidLPError, InvalidPoolError) as invalid_error:
            logger.warning("Invalid pool data found: %s", invalid_error)

        except KeyError as key_error:
            logger.error("Error accessing asset data: %s", key_error)

        return None

    @staticmethod
    async def fetch_dex_rate(name: str, asset_a: str, asset_b: str) -> Optional[float]:
        """Fetches rate information from a single DEX.

        Args:
            name (str): The name of the DEX.
            asset_a (str): The first asset in the pair.
            asset_b (str): The second asset in the pair.

        Returns:
            Optional[dict[str, Any]]: A dictionary containing the source and price, or None if an error occurs.
        """
        try:
            dex = SUPPORTED_DEXES.get(name)
            if not dex:
                logger.warning("Unsupported DEX: %s", name)
                return None

            if name == "vyfi":
                # Special handling for VyFi DEX
                selector = dex.pool_selector(assets=[asset_a, asset_b]).model_dump()
                assets = selector.pop("assets", [])
            else:
                # Original handling for other DEXes
                selector = dex.pool_selector().model_dump()
                assets = selector.pop("assets") or []
                assets.extend([a for a in [asset_a, asset_b] if a != "lovelace"])

            result = await asyncio.to_thread(
                get_backend().get_pool_utxos,
                limit=10,
                assets=assets,
                historical=False,
                **selector,
            )
            for record in result:
                try:
                    pool = dex.model_validate(record.model_dump())
                    price = Charli3DendriteAdapter.get_correct_price(
                        pool, [asset_a, asset_b]
                    )

                    if price:
                        logger.info(
                            "%s - %s - POOL_ID: %s",
                            dex.dex(),
                            price,
                            pool.pool_id,
                        )
                        return float(price)
                except (NoAssetsError, InvalidLPError, InvalidPoolError) as e:
                    logger.warning("Invalid pool data in %s: %s", dex.dex(), e)
                    continue

        except Exception as dex_error:
            logger.error("Error fetching Pool Utxos for %s: %s", name, dex_error)

        return None

    @staticmethod
    def remove_label_and_decode(asset_name_hex: str) -> str:
        """Removes the CIP-68 label from the asset name, decodes the label, and decodes the remaining asset name."""

        asset_bytes = bytes.fromhex(asset_name_hex)

        remaining_bytes = asset_bytes[4:]

        try:
            decoded_name = remaining_bytes.decode("utf-8")
        except UnicodeDecodeError:
            decoded_name = remaining_bytes.hex()

        return decoded_name

    def _log_sources_summary(self) -> None:
        """Provides a summary of sources specific to Charli3DendriteAdapter."""
        logger.info("SOURCES:")
        for source in self.sources:
            logger.info("  - %s", source)
