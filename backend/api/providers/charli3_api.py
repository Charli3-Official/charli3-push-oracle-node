"""This module contains the Charli3Api class, which encapsulates interaction with C3 Networks using Blockfrost/Ogmios services."""

import logging
from typing import Optional
from charli3_offchain_core.chain_query import ChainQuery
from charli3_offchain_core.oracle_checks import c3_get_rate
from pycardano import MultiAsset
from .coinrate import CoinRate
from .api import UnsuccessfulResponse


logger = logging.getLogger(__name__)


class Charli3Api(CoinRate):
    """Encapsulates interaction with C3 Networks using Blockfrost/Ogmios services.
    Attributes:
            provider (str): Name of the data provider.
            network_tokens (str): Tokens used in the network.
            network_address (str): C3 Network address.
            network_minting_policy (str): Network minting policy.
            quote_currency (bool): Flag for quote currency. Defaults to True.
            rate_calculation_method (str): Method for rate calculation. Defaults to 'multiply'.

    This class should be exclusively used as the quote currency, as it leverages the C3 Network.
    There is no necessity to utilize additional quote currencies in conjunction with this one.
    """

    def __init__(
        self,
        provider: str,
        network_tokens: str,
        network_address: str,
        network_minting_policy: str,
        quote_currency: bool = False,
        rate_calculation_method: str = "multiply",
        provider_id: Optional[str] = None,
    ):
        self.provider = provider
        self.network_tokens = network_tokens
        self.network_address = network_address
        self.network_minting_policy = network_minting_policy
        self.quote_currency = quote_currency
        self.rate_calculation_method = rate_calculation_method
        self.provider_id = provider_id

    async def get_rate(
        self,
        chain_query: ChainQuery = None,
        quote_currency_rate: Optional[float] = None,
        quote_symbol: Optional[str] = None,
    ):
        """Retrieves the C3 Network exchange rate and calculates its decimal representation.

        Args:
            chain_query (ChainQuery): The chain query object.
            quote_currency_rate (float, optional): The rate of the quote currency. Defaults to None.

        Returns:
            Optional[float]: The calculated rate or None if an error occurs.
        """
        try:
            logger.info("Getting C3 Network feed %s", self.network_tokens)

            if not chain_query:
                logger.critical("ChainQuery object not found")
                return self._construct_response_dict(
                    self.provider_id,
                    self.network_tokens,
                    self.network_tokens,
                    None,
                    None,
                    "ChainQuery object not found",
                )

            c3_network_utxos = await chain_query.get_utxos(self.network_address)

            oracle_nft = MultiAsset.from_primitive(
                {self.network_minting_policy: {b"OracleFeed": 1}}
            )

            c3_integer_price, _ = c3_get_rate(c3_network_utxos, oracle_nft)
            c3_decimal_price = c3_integer_price / 1000000
            logger.info("C3 Network price %s", c3_decimal_price)

            (rate, output_symbol) = self._calculate_final_rate(
                self.quote_currency,
                c3_decimal_price,
                quote_currency_rate,
                self.rate_calculation_method,
                self.network_address,
                quote_symbol,
            )
            logger.info("%s %s Rate: %s", self.provider, output_symbol, rate)
            return self._construct_response_dict(
                self.provider_id, self.network_tokens, output_symbol, None, rate
            )

        except UnsuccessfulResponse as e:  # pylint: disable=invalid-name
            logger.error(
                "Failed to get rate for Charli3Api %s: %s", self.network_tokens, e
            )
            return self._construct_response_dict(
                self.provider_id,
                self.network_tokens,
                self.network_tokens,
                None,
                None,
                str(e),
            )
