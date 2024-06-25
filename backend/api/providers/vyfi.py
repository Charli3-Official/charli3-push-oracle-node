"""This module contains the VyFi API class, which interacts with the VyFi Dex to provide token swap rates."""

import logging
from typing import Any, Dict, Optional

from charli3_offchain_core.backend import UnsuccessfulResponse
from charli3_offchain_core.chain_query import ChainQuery
from pycardano import AssetName, ScriptHash, UTxO

from .coinrate import CoinRate
from .datums import VyFiBarFees

logger = logging.getLogger(__name__)


class VyFiApi(CoinRate):
    """This class encapsulates the interaction with the VyFi Dex"""

    def __init__(
        self,
        provider: str,
        pool_tokens: str,
        pool_address: str,
        minting_a_token_policy: str,
        minting_b_token_policy: str,
        get_second_pool_price: bool = False,
        quote_currency: bool = False,
        rate_calculation_method: str = "multiply",
        rate_type: str = "base",
        provider_id: Optional[str] = None,
    ):
        self.provider = provider
        self.pool_tokens = pool_tokens
        self.pool_address = pool_address
        self.minting_a_policy = minting_a_token_policy
        self.minting_b_policy = minting_b_token_policy
        self.get_second_pool_price = get_second_pool_price
        self.quote_currency = quote_currency
        self.rate_calculation_method = rate_calculation_method
        self.rate_type = rate_type
        self.provider_id = provider_id
        self.min_ada_per_utxo = 2000000  # Min ADA required per UTxO

    async def get_rate(
        self,
        chain_query: Optional[ChainQuery] = None,
        quote_currency_rate: Optional[float] = None,
        quote_symbol: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        try:
            logger.info("Getting VyFi pool value for tokens: %s", self.pool_tokens)

            if chain_query is None:
                logger.critical("ChainQuery object not found")
                return self._construct_response_dict(
                    self.provider_id,
                    self.pool_tokens,
                    self.pool_tokens,
                    self.rate_type,
                    None,
                    None,
                    "ChainQuery object not found",
                )

            # Split the assets we are looking for in the pool
            token_a, token_b = self.pool_tokens.split("-")

            # Logic for assets pairs that involve lovelace
            if token_a == "ADA":
                token_b_script_hash = self._get_script_hash(
                    token_b, self.minting_b_policy
                )

                # Retrieve all UTXOs containing the token B
                matching_utxos = await self._get_matching_utxos_from_script_hash(
                    token_b_script_hash, chain_query
                )

                if len(matching_utxos) != 1:
                    logger.critical(
                        "Expected one UTxO with token B, found %d", len(matching_utxos)
                    )
                    return self._construct_response_dict(
                        self.provider_id,
                        self.pool_tokens,
                        self.pool_tokens,
                        self.rate_type,
                        None,
                        None,
                        "Expected one UTxO with token B, found %d",
                    )

                pool_utxo = matching_utxos[0]

                # Get tokens amounts
                ada_amount = pool_utxo.output.amount.coin
                token_b_amount = self._get_token_amount(
                    pool_utxo, token_b, token_b_script_hash
                )

                # Get datum's fees
                bar_fees_datum = await self._get_bar_fees_datum(chain_query, pool_utxo)
                if not bar_fees_datum:
                    logger.critical("Bar fees datum not found")
                    return self._construct_response_dict(
                        self.provider_id,
                        self.pool_tokens,
                        self.pool_tokens,
                        self.rate_type,
                        None,
                        None,
                        "Bar fees datum not found",
                    )

                # Adjust tokens amounts by subtracting the fees.
                adjusted_token_a = (
                    ada_amount - bar_fees_datum.token_a_fees - self.min_ada_per_utxo
                )
                adjusted_token_b = token_b_amount - bar_fees_datum.token_b_fees

            # Logic for assets pairs that doesn't involve lovelace
            else:
                token_a_script_hash = self._get_script_hash(
                    token_a, self.minting_a_policy
                )
                token_b_script_hash = self._get_script_hash(
                    token_b, self.minting_b_policy
                )

                # Retrieve all UTXOs containing the token B
                matching_utxos = await self._get_matching_utxos_from_script_hashes(
                    token_a_script_hash, token_b_script_hash, chain_query
                )

                if len(matching_utxos) != 1:
                    logger.critical(
                        "Expected one UTxO with token A and B, found %d",
                        len(matching_utxos),
                    )
                    return self._construct_response_dict(
                        self.provider_id,
                        self.pool_tokens,
                        self.pool_tokens,
                        self.rate_type,
                        None,
                        None,
                        "Expected one UTxO with token A and B, found %d",
                    )

                pool_utxo = matching_utxos[0]

                token_a_amount = self._get_token_amount(
                    pool_utxo, token_a, token_a_script_hash
                )
                token_b_amount = self._get_token_amount(
                    pool_utxo, token_b, token_b_script_hash
                )

                # Get datum's fees
                bar_fees_datum = await self._get_bar_fees_datum(chain_query, pool_utxo)
                if not bar_fees_datum:
                    logger.critical("Bar fees datum not found")
                    return self._construct_response_dict(
                        self.provider_id,
                        self.pool_tokens,
                        self.pool_tokens,
                        self.rate_type,
                        None,
                        None,
                        "Bar fees datum not found",
                    )

                # Adjust tokens amounts by subtracting the fees.
                adjusted_token_a = token_a_amount - bar_fees_datum.token_a_fees
                adjusted_token_b = token_b_amount - bar_fees_datum.token_b_fees

            # Compute the base rate.
            base_rate = (
                adjusted_token_a / adjusted_token_b
                if not self.get_second_pool_price
                else adjusted_token_b / adjusted_token_a
            )

            # Get symbol
            symbol = self.get_symbol(token_a, token_b)

            # Calculate the final rate.
            (rate, output_symbol) = self._calculate_final_rate(
                self.quote_currency,
                base_rate,
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
            logger.error("Failed to get rate for VyFi %s: %s", self.pool_tokens, e)
            return self._construct_response_dict(
                self.provider_id,
                self.pool_tokens,
                self.pool_tokens,
                self.rate_type,
                None,
                None,
                str(e),
            )

    def get_symbol(self, token_a, token_b) -> str:
        """Display log information according to the rate."""
        if not self.get_second_pool_price:
            return f"{token_b} - {token_a}"
        else:
            return f"{token_a} - {token_b}"

    async def _get_bar_fees_datum(self, chain_query, pool_utxo):
        """
        Retrieves the bar fees datum from a given pool UTxO.

        Args:
            chain_query: The chain query object used for fetching data.
            pool_utxo: The UTxO of the pool, which contains the datum or datum hash.

        Returns:
            The bar fees extracted from the UTxO's datum, or None if not found.
        """
        datum_hash = pool_utxo.output.datum_hash
        if datum_hash is not None:
            # Fetch and decode the datum from its hash
            cbor_data = chain_query.context.api.script_datum_cbor(str(datum_hash)).cbor
            return VyFiBarFees.from_cbor(cbor_data)
        if pool_utxo.output.datum is not None:
            # Directly use the datum if it's present
            return VyFiBarFees.from_cbor(pool_utxo.output.datum.cbor)

        logger.critical("Bar fees datum not found in the pool UTxO.")
        return self._construct_response_dict(
            self.provider_id,
            self.pool_tokens,
            self.pool_tokens,
            self.rate_type,
            None,
            None,
            "Bar fees datum not found in the pool UTxO.",
        )

    async def _get_matching_utxos_from_script_hash(
        self, token_script_hash: ScriptHash, chain_query: ChainQuery
    ):
        """Get the UTxOs containing the required script hash"""
        return [
            utxo
            for utxo in await chain_query.get_utxos(self.pool_address)
            if any(
                script_hash == token_script_hash
                for script_hash in utxo.output.amount.multi_asset
            )
        ]

    async def _get_matching_utxos_from_script_hashes(
        self,
        token_a_script_hash: ScriptHash,
        token_b_script_hash: ScriptHash,
        chain_query: ChainQuery,
    ):
        """Retrieve the UTXOs containing the specified script hashes"""
        all_utxos = await chain_query.get_utxos(self.pool_address)
        matching_utxos = []

        for utxo in all_utxos:
            script_hashes = utxo.output.amount.multi_asset.keys()

            if (
                token_a_script_hash in script_hashes
                and token_b_script_hash in script_hashes
            ):
                matching_utxos.append(utxo)

        return matching_utxos

    def _get_token_amount(
        self, pool_utxo: UTxO, token_name: str, token_script_hash: ScriptHash
    ):
        """Retrieve the token amount associated with a specified asset name and script hash"""
        token_asset_name = AssetName(token_name.encode())
        return pool_utxo.output.amount.multi_asset[token_script_hash].get(
            token_asset_name, 0
        )

    def _get_script_hash(self, token_name: str, policy_id: str):
        """Retrieve the associated script hash"""
        token_script_hash = ScriptHash(bytes.fromhex(policy_id))
        logger.info(
            "Target script hash for token %s: %s",
            token_name,
            token_script_hash,
        )
        return token_script_hash
