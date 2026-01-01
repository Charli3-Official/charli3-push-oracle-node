"""
LP Token Pricing Adapter - Calculates NAV-based pricing for DEX LP tokens.

Formula for ADA-paired pools: LP_price = (Total_ADA_in_pool × 2) / Total_LP_tokens_minted

This adapter:
1. Queries a specific DEX pool by LP token ID
2. Extracts on-chain pool reserves and LP token supply from pool state
3. Calculates LP token price using NAV (Net Asset Value) formula
4. Returns price in standard adapter format for aggregation

Supports: VyFi (initial), expandable to Minswap, Spectrum, etc.
"""

import asyncio
import binascii
import logging
from decimal import Decimal
from typing import Any, Optional

from charli3_dendrite import MinswapV2CPPState, SpectrumCPPState, VyFiCPPState
from charli3_dendrite.backend import get_backend
from charli3_dendrite.dexs.amm.minswap import MinswapV2PoolDatum
from charli3_dendrite.dexs.amm.spectrum import SpectrumPoolDatum
from charli3_dendrite.dexs.amm.vyfi import VyFiPoolDatum
from charli3_dendrite.dexs.core.errors import (
    InvalidLPError,
    InvalidPoolError,
    NoAssetsError,
)

from backend.api.providers.base_adapter import BaseAdapter

logger = logging.getLogger(__name__)

# Map DEX names to their pool state classes
SUPPORTED_LP_DEXES = {
    "vyfi": VyFiCPPState,
    "minswapv2": MinswapV2CPPState,
    "spectrum": SpectrumCPPState,
}

SCRIPT_HASH_SIZE = 28


class LPTokenAdapter(BaseAdapter):
    """
    Adapter for pricing LP tokens using on-chain NAV calculation.

    Args:
        pool_dex: DEX name (e.g., "vyfi", "minswapv2")
        pool_assets: List of assets in the pool [asset_a, asset_b] for querying specific pool
        pair_type: "base" or "quote" (for rate type classification)
    """

    def __init__(
        self,
        pool_dex: str,
        pool_assets: list[str],
        pair_type: str,
        quote_required: Optional[bool] = False,
        quote_calc_method: Optional[str] = None,
    ):  # pylint: disable=too-many-arguments
        if pool_dex not in SUPPORTED_LP_DEXES:
            raise ValueError(f"Unsupported LP DEX: {pool_dex}")

        # Validate pool_assets
        if len(pool_assets) != 2:
            raise ValueError(
                f"pool_assets must contain exactly 2 assets, got {len(pool_assets)}"
            )

        if "lovelace" not in pool_assets:
            raise ValueError(
                "LP token adapter currently only supports ADA-paired pools. "
                "pool_assets must include 'lovelace'"
            )

        # Validate asset IDs (non-lovelace)
        for asset in pool_assets:
            if asset != "lovelace":
                try:
                    # Check if it's a valid hex string
                    int(asset, 16)
                except ValueError as exc:
                    raise ValueError(
                        f"Invalid asset ID format: {asset}. Expected hex string or 'lovelace'"
                    ) from exc

        # For LP tokens, use pool_dex as identifier
        lp_token_name = self._generate_lp_token_name(pool_dex, pool_assets)

        super().__init__(
            asset_a=lp_token_name,  # Generated LP token name
            asset_b="ADA",  # LP tokens are priced in ADA
            pair_type=pair_type,
            sources=[pool_dex],
            quote_required=quote_required,
            quote_calc_method=quote_calc_method,
        )
        self.pool_dex = pool_dex
        self.pool_assets = pool_assets

    async def get_rates(self) -> Optional[dict[str, Any]]:
        """
        Fetch LP token price from specified DEX pool(s).

        Returns:
            dict with structure:
            {
                "asset_a_name": "LP_TOKEN_NAME",
                "asset_b_name": "ADA",
                "rates": [
                    {
                        "source": "vyfi",
                        "source_id": "provider_id",
                        "price": 1.234  # LP token price in ADA
                    }
                ]
            }
        """
        asset_a_name, asset_b_name = self.get_asset_names()
        rates = []

        logger.info(
            "------------------------------------------------------------------"
        )
        logger.info(
            "--------------- LP Token Adapter - %s - %s ---------------",
            asset_a_name,
            asset_b_name,
        )
        logger.info(
            "------------------------------------------------------------------"
        )

        try:
            # Query each DEX source
            batch_requests = [
                self._fetch_lp_price(dex_name) for dex_name in self.sources
            ]
            results = await asyncio.gather(*batch_requests)

            for dex_name, result in zip(self.sources, results):
                if result:
                    rates.append(
                        {
                            "source": dex_name,
                            "price": result,
                            "source_id": super().get_source_id(dex_name),
                        }
                    )
        except Exception as error:  # pylint: disable=broad-exception-caught
            logger.error("Critical error in get_rates: %s", error)
            return None

        if rates:
            return {
                "asset_a_name": asset_a_name,
                "asset_b_name": asset_b_name,
                "rates": rates,
            }

        logger.warning(
            "No matching LP pool found for %s with assets %s",
            self.pool_dex,
            self.pool_assets,
        )
        return None

    def _generate_lp_token_name(self, dex: str, pool_assets: list[str]) -> str:
        """
        Generate a descriptive LP token name from DEX and pool assets.

        Args:
            dex: DEX name
            pool_assets: List of pool assets

        Returns:
            Generated LP token name (e.g., "SNEK-ADA-LP-vyfi")
        """
        # Extract asset names from pool_assets
        asset_names = []
        for asset in pool_assets:
            if asset == "lovelace":
                asset_names.append("ADA")
            else:
                # Try to extract and decode asset name
                # Format: policy_id (56 chars) + asset_name (hex)
                if len(asset) > 56:
                    asset_name_hex = asset[56:]
                    try:
                        decoded = binascii.unhexlify(asset_name_hex).decode("utf-8")
                        # Use decoded name if it's printable
                        if decoded.isprintable() and decoded.strip():
                            asset_names.append(decoded.upper())
                        else:
                            # Fallback to hex if not printable
                            asset_names.append(asset[-12:].upper())
                    except (binascii.Error, UnicodeDecodeError):
                        # Fallback if decoding fails
                        asset_names.append(asset[-12:].upper())
                else:
                    # Just policy ID or short hex
                    asset_names.append(asset[-8:].upper())

        return f"{'-'.join(asset_names)}-LP-{dex}"

    def get_lp_token_name(self) -> str:
        """
        Returns the LP token name.

        Returns:
            LP token name
        """
        return self._generate_lp_token_name(self.pool_dex, self.pool_assets)

    def get_asset_names(self) -> tuple[str, str]:
        """
        Returns asset names for the LP token.

        Returns:
            Tuple of (LP_TOKEN_NAME, "ADA")
        """
        return self.get_lp_token_name(), "ADA"

    async def _fetch_lp_price(self, dex_name: str) -> Optional[float]:
        """
        Fetch LP token price from a specific DEX.

        Args:
            dex_name: DEX to query ("vyfi", "minswapv2", etc.)

        Returns:
            LP token price in ADA or None if not found
        """
        try:
            pool_state = await self._query_pool_by_assets(dex_name)
            if pool_state:
                lp_price = self._calculate_lp_nav_price(pool_state)
                logger.info(
                    "%s - LP Token Price: %s ADA - Pool: %s",
                    dex_name,
                    lp_price,
                    pool_state.pool_id,
                )
                return float(lp_price)
        except Exception as error:  # pylint: disable=broad-exception-caught
            logger.error("Error fetching LP price from %s: %s", dex_name, error)

        return None

    def _select_best_pool(self, matching_pools: list[Any], dex_name: str) -> Any:
        """Select the best pool from a list of matching pools based on TVL."""
        if not matching_pools:
            return None

        if len(matching_pools) == 1:
            pool = matching_pools[0]
            logger.info(
                "Found pool %s for assets %s",
                pool.pool_id,
                self.pool_assets,
            )
            return pool

        logger.warning(
            "Found %d matching pools for %s on %s. Selecting highest TVL.",
            len(matching_pools),
            self.pool_assets,
            dex_name,
        )

        def get_safe_tvl(pool):
            try:
                return pool.tvl
            except Exception:  # pylint: disable=broad-exception-caught
                # Fallback: calculate TVL based on ADA reserves
                try:
                    assets = pool.assets.model_dump()
                    if "lovelace" in assets:
                        # TVL = ADA amount * 2 (roughly)
                        return Decimal(assets["lovelace"]) / Decimal(1_000_000) * 2
                except Exception:  # pylint: disable=broad-exception-caught
                    pass
                return Decimal(0)

        # Sort by TVL descending
        matching_pools.sort(key=get_safe_tvl, reverse=True)
        selected_pool = matching_pools[0]

        logger.info(
            "Selected pool %s with TVL %s ADA (Next highest: %s ADA)",
            selected_pool.pool_id,
            get_safe_tvl(selected_pool),
            (get_safe_tvl(matching_pools[1]) if len(matching_pools) > 1 else "N/A"),
        )
        return selected_pool

    async def _query_pool_by_assets(self, dex_name: str) -> Optional[Any]:
        """
        Query a specific pool by its trading pair assets.

        Args:
            dex_name: DEX to query ("vyfi", "minswapv2", etc.)

        Returns:
            Pool state object or None if not found
        """
        try:
            dex_class = SUPPORTED_LP_DEXES.get(dex_name)
            if not dex_class:
                logger.warning("Unsupported DEX: %s", dex_name)
                return None

            # Get pool selector for this DEX with the specific trading pair
            if dex_name == "vyfi":
                # VyFi requires assets in the selector to find the specific pool
                selector = dex_class.pool_selector(assets=self.pool_assets).model_dump()
                query_assets = []
            else:
                # Other DEXes use standard selector
                selector = dex_class.pool_selector().model_dump()
                query_assets = [a for a in self.pool_assets if a != "lovelace"]

            result = await asyncio.to_thread(
                get_backend().get_pool_utxos,
                addresses=selector.get("addresses"),
                limit=10,
                assets=query_assets,
                historical=False,
            )

            matching_pools = []

            # Collect all valid pools for this trading pair
            for record in result:
                try:
                    record_dict = record.model_dump()
                    if record_dict.get("datum_hash") is None:
                        record_dict["datum_hash"] = ""
                    if record_dict.get("datum_cbor") is None:
                        record_dict["datum_cbor"] = ""

                    pool = dex_class.model_validate(record_dict)

                    # Verify pool has the expected assets
                    pool_assets = pool.assets.model_dump()
                    has_all_assets = all(
                        asset in pool_assets for asset in self.pool_assets
                    )

                    if has_all_assets:
                        matching_pools.append(pool)

                except (NoAssetsError, InvalidLPError, InvalidPoolError) as exc:
                    logger.debug("Invalid pool data: %s", exc)
                    continue
                except Exception as exc:  # pylint: disable=broad-exception-caught
                    logger.debug("Error processing pool: %s", exc)
                    continue

            if not matching_pools:
                logger.warning(
                    "No pool found for assets %s on %s", self.pool_assets, dex_name
                )
                return None

            return self._select_best_pool(matching_pools, dex_name)

        except Exception as error:  # pylint: disable=broad-exception-caught
            logger.error("Error querying pool: %s", error)
            return None

    def _extract_lp_supply_from_datum(self, pool_state: Any) -> Optional[int]:
        """Extract LP token supply from pool datum (CBOR)."""
        try:
            if hasattr(pool_state, "datum_cbor") and pool_state.datum_cbor:
                datum = None
                if self.pool_dex == "vyfi":
                    datum = VyFiPoolDatum.from_cbor(pool_state.datum_cbor)
                    if hasattr(datum, "lp_tokens"):
                        logger.debug("Parsed VyFi datum.lp_tokens: %s", datum.lp_tokens)
                        return datum.lp_tokens

                elif self.pool_dex == "minswapv2":
                    datum = MinswapV2PoolDatum.from_cbor(pool_state.datum_cbor)
                    if hasattr(datum, "total_liquidity"):
                        logger.debug(
                            "Parsed MinswapV2 datum.total_liquidity: %s",
                            datum.total_liquidity,
                        )
                        return datum.total_liquidity

                elif self.pool_dex == "spectrum":
                    datum = SpectrumPoolDatum.from_cbor(pool_state.datum_cbor)
                    if hasattr(datum, "pool_lp_amount"):
                        logger.debug(
                            "Parsed Spectrum datum.pool_lp_amount: %s",
                            datum.pool_lp_amount,
                        )
                        return datum.pool_lp_amount
                    if hasattr(datum, "lp_tokens"):
                        logger.debug(
                            "Parsed Spectrum datum.lp_tokens: %s", datum.lp_tokens
                        )
                        return datum.lp_tokens
        except Exception as error:  # pylint: disable=broad-exception-caught
            logger.debug("Error parsing datum from CBOR: %s", error)
        return None

    def _extract_lp_supply_fallback(self, pool_state: Any) -> Optional[int]:
        """Fallback methods to extract LP token supply."""
        # 2. Fallback: try pool-level attributes (older approach)
        if hasattr(pool_state, "pool_datum") and pool_state.pool_datum:
            if hasattr(pool_state.pool_datum, "lp_tokens"):
                logger.debug(
                    "Using VyFi pool_datum.lp_tokens: %s",
                    pool_state.pool_datum.lp_tokens,
                )
                return pool_state.pool_datum.lp_tokens
            if hasattr(pool_state.pool_datum, "total_liquidity"):
                logger.debug(
                    "Using MinswapV2 pool_datum.total_liquidity: %s",
                    pool_state.pool_datum.total_liquidity,
                )
                return pool_state.pool_datum.total_liquidity
            if hasattr(pool_state.pool_datum, "circulation_lp"):
                logger.debug(
                    "Using SundaeSwapV3 pool_datum.circulation_lp: %s",
                    pool_state.pool_datum.circulation_lp,
                )
                return pool_state.pool_datum.circulation_lp

        # 3. Last resort: try direct pool attributes
        if hasattr(pool_state, "total_liquidity"):
            logger.debug("Using pool.total_liquidity: %s", pool_state.total_liquidity)
            return pool_state.total_liquidity
        if hasattr(pool_state, "lp_token") and hasattr(pool_state.lp_token, "quantity"):
            logger.debug(
                "Using pool.lp_token.quantity(): %s", pool_state.lp_token.quantity()
            )
            return pool_state.lp_token.quantity()

        return None

    def _extract_lp_supply(self, pool_state: Any) -> Optional[int]:
        """Extract LP token supply from pool state using various methods."""
        # 1. Try explicit datum parsing from CBOR (most robust)
        total_lp_tokens = self._extract_lp_supply_from_datum(pool_state)
        if total_lp_tokens is not None:
            return total_lp_tokens

        # 2. Fallback methods
        return self._extract_lp_supply_fallback(pool_state)

    def _calculate_lp_nav_price(self, pool_state: Any) -> Decimal:
        """
        Calculate NAV-based LP token price.

        Formula: LP_price (in ADA) = (Total_ADA_in_pool × 2) / Total_LP_tokens_minted / 1_000_000

        Note: LP tokens typically have 0 decimals (indivisible), while ADA has 6 decimals.
        Returns price in ADA (standard units) to match other adapters.

        Args:
            pool_state: Pool state object with reserves and LP token data

        Returns:
            LP token price in ADA per LP token

        Raises:
            ValueError: If pool is not ADA-paired or data is invalid
        """
        try:
            # Get pool assets to verify ADA pairing
            pool_assets = pool_state.assets.model_dump()

            # Verify this is an ADA-paired pool
            if "lovelace" not in pool_assets:
                raise ValueError(f"Pool {pool_state.pool_id} is not ADA-paired")

            # Get ADA reserves in lovelace
            ada_reserve_lovelace = pool_assets["lovelace"]

            # Get total LP tokens minted
            total_lp_tokens = self._extract_lp_supply(pool_state)

            if total_lp_tokens is None:
                raise ValueError(
                    f"Cannot determine total LP tokens for pool {pool_state.pool_id}. "
                    f"Pool type: {type(pool_state).__name__}"
                )

            # Validate values
            if ada_reserve_lovelace <= 0:
                raise ValueError(f"Invalid ADA reserve: {ada_reserve_lovelace}")
            if total_lp_tokens <= 0:
                raise ValueError(
                    f"Invalid LP token supply: {total_lp_tokens}. "
                    "Cannot calculate NAV price for pool with zero or "
                    "negative LP token supply."
                )

            # Calculate NAV: (ADA_reserves × 2) / LP_supply
            # Note: LP tokens typically have 0 decimals (indivisible)
            # First get price in lovelace, then convert to ADA (standard units)
            lp_price_lovelace = (Decimal(ada_reserve_lovelace) * 2) / Decimal(
                total_lp_tokens
            )
            lp_price_ada = lp_price_lovelace / Decimal(1_000_000)

            return lp_price_ada

        except Exception as error:
            logger.error("Error calculating LP NAV price: %s", error)
            raise

    def get_sources(self) -> list[str]:
        """Returns the DEX sources names registered for the adapter."""
        return self.sources

    @staticmethod
    def _remove_label_and_decode(asset_name_hex: str) -> str:
        """
        Removes the CIP-68 label from the asset name, decodes the label,
        and decodes the remaining asset name.
        """
        asset_bytes = bytes.fromhex(asset_name_hex)
        remaining_bytes = asset_bytes[4:]

        try:
            decoded_name = remaining_bytes.decode("utf-8")
        except UnicodeDecodeError:
            decoded_name = remaining_bytes.hex()

        return decoded_name

    def _log_sources_summary(self) -> None:
        """Provides a summary of sources specific to LP Token Adapter."""
        logger.info("SOURCES:")
        for source in self.sources:
            logger.info("  - %s", source)
        logger.info("LP Token Name: %s", self.get_lp_token_name())
        logger.info("Pool DEX: %s", self.pool_dex)
        logger.info("Pool Assets: %s", self.pool_assets)
