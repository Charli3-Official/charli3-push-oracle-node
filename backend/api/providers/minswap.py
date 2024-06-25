"""This module abstracts the interaction with the Minswap Python SDK."""

import logging
from decimal import Decimal
from typing import Dict, Optional, Tuple

from charli3_offchain_core.backend import KupoContext, UnsuccessfulResponse
from charli3_offchain_core.chain_query import ChainQuery
from pycardano import AssetName, ScriptHash, UTxO

from .coinrate import CoinRate

logger = logging.getLogger(__name__)


class MinswapApi(CoinRate):
    """
    This class abstracts the interaction with the Minswap.

    Attributes:
        provider (str): Identifier for the rate provider.
        pool_tokens (str): The trading pair in the liquidity pool.
        pool_id (str): Unique identifier for the liquidity pool.
        get_second_pool_price (bool): Flag to choose which pool price to use.
        quote_currency (bool): Flag to indicate if the quote currency rate should be used.
        rate_calculation_method (str): Method for rate calculation (e.g., "multiply").

    Methods:
        get_rate: Retrieves the exchange rate from the Minswap pool.
    """

    def __init__(
        self,
        provider: str,
        token_a_name: str,
        token_a_decimal: int,
        token_b_name: str,
        token_b_decimal: int,
        pool_id: str,
        get_second_pool_price: bool = False,
        quote_currency: bool = False,
        rate_calculation_method: str = "multiply",
        rate_type: str = "base",
        provider_id: Optional[str] = None,
    ):
        self.provider = provider
        self.token_a = token_a_name
        self.token_b = token_b_name
        self.pool_tokens = f"{self.token_a}-{self.token_b}"
        self.token_a_decimal = token_a_decimal
        self.token_b_decimal = token_b_decimal
        self.pool_id = pool_id
        self.get_second_pool_price = get_second_pool_price
        self.quote_currency = quote_currency
        self.rate_calculation_method = rate_calculation_method
        self.rate_type = rate_type
        self.pool_nft_policy_id = (
            "0be55d262b29f564998ff81efe21bdc0022621c12f15af08d0f2ddb1"
        )
        self.factory_policy_id = (
            "13aa2accf2e1561723aa26871e071fdf32c867cff7e7d50ad470d62f"
        )
        self.factory_asset_name = "4d494e53574150"  # MINSWAP
        self.provider_id = provider_id

    async def get_rate(
        self,
        chain_query: Optional[ChainQuery] = None,
        quote_currency_rate: Optional[float] = None,
        quote_symbol: Optional[str] = None,
    ):
        if chain_query is None:
            logger.error(
                "Chain query is None. Cannot get Minswap %s-%s pool value",
                self.token_a,
                self.token_b,
            )
            return self._construct_response_dict(
                self.provider_id,
                self.pool_tokens,
                self.pool_tokens,
                self.rate_type,
                None,
                None,
                "Chain query or Blockfrost context is None",
            )
        try:
            logger.info("Getting Minswap %s-%s pool value", self.token_a, self.token_b)

            # Pool UTxO
            pool = await self._get_and_validate_pool(self.pool_id, chain_query)

            # Get the correct symbols
            symbol = self._get_symbol(pool)

            price_to_buy_token_b, price_to_buy_token_a = self._price(pool)

            if self.get_second_pool_price is False:
                base_rate = price_to_buy_token_b
            else:
                base_rate = price_to_buy_token_a

            (rate, output_symbol) = self._calculate_final_rate(
                self.quote_currency,
                float(base_rate),
                quote_currency_rate,
                self.rate_calculation_method,
                symbol,
                quote_symbol,
            )

            logger.info("%s %s Rate: %s", self.provider, output_symbol, rate)
            return self._construct_response_dict(
                self.provider_id,
                self.pool_tokens,
                output_symbol,
                self.rate_type,
                None,
                rate,
            )
        except UnsuccessfulResponse as e:  # pylint: disable=invalid-name
            logger.error(
                "Failed to get rate for Minswap %s-%s: %s",
                self.token_a,
                self.token_b,
                e,
            )
            return self._construct_response_dict(
                self.provider_id,
                self.pool_tokens,
                self.pool_tokens,
                self.rate_type,
                None,
                None,
                str(e),
            )

        except TimeoutError as e:
            logger.error(
                "Timeout error occurred while fetching Minswap %s-%s pool value: %s",
                self.token_a,
                self.token_b,
                e,
            )
            return self._construct_response_dict(
                self.provider_id,
                self.pool_tokens,
                self.pool_tokens,
                self.rate_type,
                None,
                None,
                "Timeout error",
            )

        except Exception as e:
            logger.error(
                "Failed to get rate for Minswap %s-%s: %s",
                self.token_a,
                self.token_b,
                e,
            )
            return self._construct_response_dict(
                self.provider_id,
                self.pool_tokens,
                self.pool_tokens,
                self.rate_type,
                None,
                None,
                str(e),
            )

    async def _get_and_validate_pool(self, pool_id, chain_query):
        """Get and validate pool utxo"""
        pool = await self._get_pool_by_id(pool_id, chain_query)
        if not self._check_valid_pool_output(pool):
            logger.error(
                "Factory token not located in the pool, or multiple tokens detected"
            )
            return self._construct_response_dict(
                self.provider_id,
                self.pool_tokens,
                self.pool_tokens,
                self.rate_type,
                None,
                None,
                "Factory token not located in the pool, or multiple tokens detected",
            )
        return pool

    def _check_valid_pool_output(self, pool: UTxO) -> bool:
        """Determine if the pool address is valid.

        Args:
            pool: A UTxO representing the pool.

        Returns:
            bool: True if valid, False otherwise.

        Raises:
            ValueError: If the pool does not contain exactly one factory token.
        """

        # Check to make sure the pool has 1 factory token

        # token_asset_name1 = AssetName(b"MINSWAP")
        token_asset_name = AssetName(bytes.fromhex(self.factory_asset_name))
        token_script_hash = ScriptHash(bytes.fromhex(self.factory_policy_id))

        # Attempt to retrieve the amount of the factory token
        amount = pool.output.amount.multi_asset.get(token_script_hash, {}).get(
            token_asset_name, 0
        )

        if amount == 1:
            return True
        return False

    def _price(self, pool: UTxO) -> Tuple[Decimal, Decimal]:
        """Price of assets.

        Returns:
            A `Tuple[Decimal, Decimal] where the first `Decimal` is the price to buy
                1 of token B in units of token A, and the second `Decimal` is the price
                to buy 1 of token A in units of token B.
        """
        nat_assets = self._normalized_asset(pool)

        return (
            (nat_assets[self.token_a] / nat_assets[self.token_b]),
            (nat_assets[self.token_b] / nat_assets[self.token_a]),
        )

    def _get_token_amount(self, pool_utxo: UTxO, token_name: str) -> int:
        """Retrieve the total token amount associated with a specified asset name
        across all script hashes.

        Args:
            pool: Pool UTxO
            token_name: Asset name

        Returns:
            The associated asset's amount, default 0
        """
        token_asset_name = AssetName(token_name.encode())
        total_amount = 0
        for _, assets in pool_utxo.output.amount.multi_asset.items():
            token_amount = assets.get(token_asset_name)
            if token_amount:
                return token_amount
        return total_amount

    def _normalized_asset(self, pool: UTxO) -> Dict[str, Decimal]:
        """Get the number of decimals associated with an asset.

        This returns a `Decimal` with the proper precision context.

        Args:
            pool: Pool UTxO

        Returns:
            A dictionary where assets are keys and values are `Decimal` objects containing
                exact quantities of the asset, accounting for asset decimals.
        """
        nat_assets = {}
        if "ADA" == self.token_a:
            nat_assets[self.token_a] = self._asset_decimals(pool.output.amount.coin, 6)
        else:
            nat_assets[self.token_a] = self._asset_decimals(
                self._get_token_amount(pool, self.token_a),
                self.token_a_decimal,
            )
        nat_assets[self.token_b] = self._asset_decimals(
            self._get_token_amount(pool, self.token_b),
            self.token_b_decimal,
        )
        return nat_assets

    def _asset_decimals(self, amount: int, decimal: int) -> Decimal:
        """Asset decimals.

        All asset quantities are stored as integers. The decimals indicates a scaling factor
        for the purposes of human readability of asset denominations.

        For example, ADA has 6 decimals. This means every 10**6 units (lovelace) is 1 ADA.

        Args:
            unit: The policy id plus hex encoded name of an asset.

        Returns:
            The decimals for the asset.
        """
        return Decimal(amount) / Decimal(10**decimal)

    async def _get_pool_by_id(self, pool_id: str, chain_query) -> UTxO:
        """Latest UTxO of a pool.

        This method searches for the latest Unspent Transaction Output (UTxO) for
        a given pool ID. It constructs a unique identifier for the pool using a
        predefined policy ID and the pool ID.

        Args:
            pool_id: The unique identifier of the pool.

        Returns:
            The pool's latest UTxO if found, otherwise `None`.
        """
        # https://cardanosolutions.github.io/kupo/#section/Patterns
        # Polocy ID . AssetName
        nft = f"{self.pool_nft_policy_id}.{pool_id}"
        pool_utxos = await chain_query.kupo_context.utxos_kupo(nft)

        if not pool_utxos:
            return None

        if len(pool_utxos) != 1:
            logger.error("Multiple UTxO pools found, or none at all")
            return self._construct_response_dict(
                self.provider_id,
                self.pool_tokens,
                self.pool_tokens,
                self.rate_type,
                None,
                None,
                "Multiple UTxO pools found, or none at all",
            )

        return pool_utxos[0]

    def _get_symbol(self, pool: UTxO) -> str:
        """Ensure that the requested symbol corresponds exactly to the symbol retrieved through the
        on-chain query."""

        asset_a = None
        asset_b = None
        if self.token_a == "ADA":
            token_name_b = AssetName(self.token_b.encode())

            # Since ADA is not part of multi_asset, only check for token_b
            for _, assets in pool.output.amount.multi_asset.items():
                if token_name_b in assets:
                    asset_b = self.token_b
                    asset_a = "ADA"
                    break
        else:
            token_name_a = AssetName(self.token_a.encode())
            token_name_b = AssetName(self.token_b.encode())

            for _, assets in pool.output.amount.multi_asset.items():
                if token_name_a in assets:
                    asset_a = self.token_a
                if token_name_b in assets:
                    asset_b = self.token_b

        # Log error if any of the asset are not found
        if asset_a is None or asset_b is None:
            logger.error(
                f"Symbol does not match the combination of {self.token_a}-{self.token_b}",
            )
            return self._construct_response_dict(
                self.provider_id,
                self.pool_tokens,
                self.pool_tokens,
                self.rate_type,
                None,
                None,
                f"Symbol does not match the combination of {self.token_a}-{self.token_b}",
            )

        if self.get_second_pool_price:
            return f"{asset_a}/{asset_b}"
        return f"{asset_b}/{asset_a}"
