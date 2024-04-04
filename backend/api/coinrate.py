"""Exchange Api classes."""
from typing import Optional, List, Any, Dict, Tuple
import logging
import asyncio
import re

from decimal import Decimal
from charli3_offchain_core.consensus import random_median
from charli3_offchain_core.chain_query import ChainQuery
from charli3_offchain_core.oracle_checks import c3_get_rate
from pycardano import ScriptHash, UTxO, AssetName, MultiAsset
from .api import Api, UnsuccessfulResponse
from .datums import VyFiBarFees
from .kupo import Kupo

logger = logging.getLogger("CoinRate")


class CoinRate(Api):
    """Abstract coinRate class"""

    def get_path(self):
        """Path encapsulation"""

    async def get_rate(
        self, chain_query=None, quote_currency_rate=None, quote_symbol=None
    ):
        """Returns the rate accoirding to the classes instance"""

    def _get_final_symbol(
        self, base_symbol, quote_symbol: Optional[str], method
    ) -> str:
        """
        Constructs and returns a currency symbol based on the base and quote symbols and the method.
        If only one symbol is provided, it returns that symbol.
        If both are provided, it constructs a symbol based on the method ('multiply' or 'divide').
        """
        if not base_symbol:
            raise ValueError("Base symbol is required")

        # Pattern to match symbols with '-', '/', ' - ', ' / ', or ' ' as separators
        pattern = r"([A-Za-z]+)\s*[-/\s]\s*([A-Za-z]+)"
        bs_match = re.match(pattern, base_symbol, re.IGNORECASE)
        qs_match = (
            re.match(pattern, quote_symbol, re.IGNORECASE) if quote_symbol else None
        )

        # Extract symbols if they match the pattern
        bs_base, _ = bs_match.groups() if bs_match else (None, None)
        qs_base, qs_quote = qs_match.groups() if qs_match else (None, None)

        # Construct symbol based on method
        if method == "multiply" and bs_base and qs_quote:
            return f"{bs_base}/{qs_quote}".upper()
        elif method == "divide" and bs_base and qs_base:
            return f"{bs_base}/{qs_base}".upper()
        else:
            return base_symbol.upper()

    def _calculate_final_rate(
        self,
        quote_currency: bool,
        base_rate: float,
        quote_currency_rate: Optional[float],
        rate_calculation_method: str,
        base_symbol: str,
        quote_symbol: Optional[str],
    ) -> Tuple[float, str]:
        """Calculates the final rate to be returned with the correct precision"""
        symbol = self._get_final_symbol(
            base_symbol, quote_symbol, rate_calculation_method
        )
        rate: float = 0
        if quote_currency:
            if quote_currency_rate:
                if rate_calculation_method == "multiply":
                    rate = base_rate * quote_currency_rate
                elif rate_calculation_method == "divide":
                    if quote_currency_rate == 0:
                        raise ValueError(
                            "quote_currency_rate cannot be zero when rate_calculation_method is 'divide'"
                        )
                    rate = base_rate / quote_currency_rate
            else:
                raise ValueError(
                    "quote_currency_rate cannot be zero when quote_currency is True"
                )
        else:
            rate = base_rate
        rate = round(rate, 8)
        return (rate, symbol)


class Generic(CoinRate):
    """Abstracts the calls to exchange API's."""

    def __init__(
        self,
        provider: str,
        symbol: str,
        api_url: str,
        path: str,
        json_path: list[str | int],
        key: Optional[Dict[Any, Any]] = None,
        quote_currency: bool = False,
        rate_calculation_method: str = "multiply",
        token: Optional[str] = None,
    ):
        self.provider = provider
        self.symbol = symbol
        self.api_url = api_url
        self.path = path
        self.json_path = json_path
        self.key = {} if not key else key
        self.quote_currency = quote_currency
        self.rate_calculation_method = rate_calculation_method
        self.token = token

    def get_path(self) -> str:
        return self.path

    async def get_rate(
        self,
        chain_query: Optional[ChainQuery] = None,
        quote_currency_rate: Optional[float] = None,
        quote_symbol: Optional[str] = None,
    ):
        try:
            logger.info("Getting %s %s rate", self.provider, self.symbol)
            headers = self.key
            if self.token:
                # handle bearer token
                headers["Authorization"] = f"Bearer {self.token}"
            resp = await self._get(self.path, headers=headers)

            if resp.is_ok:
                data = resp.json
                for key in self.json_path:
                    if isinstance(data, dict) and isinstance(key, str) and key in data:
                        data = data[key]
                    elif (
                        isinstance(data, list)
                        and isinstance(key, int)
                        and 0 <= key < len(data)
                    ):
                        data = data[key]
                    else:
                        logger.error("Invalid path in JSON response for key: %s", key)
                        return None
                if isinstance(data, (int, float, str)):
                    (rate, output_symbol) = self._calculate_final_rate(
                        self.quote_currency,
                        float(data),
                        quote_currency_rate,
                        self.rate_calculation_method,
                        self.symbol,
                        quote_symbol,
                    )
                    logger.info("%s %s Rate: %s", self.provider, output_symbol, rate)
                    return rate
                logger.error(
                    "Data at the end of JSON path is not a number or numeric string"
                )
                return None
        except UnsuccessfulResponse as e:  # pylint: disable=invalid-name
            logger.error(
                "Failed to get rate for %s %s: %s", self.provider, self.symbol, e
            )
            return None


class BinanceApi(CoinRate):
    """Abstracts the binance API rate"""

    api_url = "https://api.binance.com"
    path = "/api/v3/ticker/price?symbol="

    def __init__(
        self,
        provider: str,
        symbol: str,
        quote_currency: bool = False,
        rate_calculation_method: str = "multiply",
    ):
        self.provider = provider
        self.symbol = symbol
        self.quote_currency = quote_currency
        self.rate_calculation_method = rate_calculation_method

    def get_path(self):
        return self.path + self.symbol

    async def get_rate(
        self,
        chain_query: Optional[ChainQuery] = None,
        quote_currency_rate: Optional[float] = None,
        quote_symbol: Optional[str] = None,
    ):
        try:
            logger.info("Getting Binance %s rate", self.symbol)
            resp = await self._get(self.get_path())
            if resp.is_ok:
                json_data = resp.json
                if json_data is not None and "price" in json_data:
                    base_rate = float(json_data["price"])
                    (rate, output_symbol) = self._calculate_final_rate(
                        self.quote_currency,
                        base_rate,
                        quote_currency_rate,
                        self.rate_calculation_method,
                        self.symbol,
                        quote_symbol,
                    )
                    logger.info("%s %s Rate: %s", self.provider, output_symbol, rate)
                    return rate
            else:
                logger.error("Response not OK for Binance %s", self.symbol)
                return None
        except UnsuccessfulResponse as e:  # pylint: disable=invalid-name
            logger.error("Failed to get rate for Binance %s: %s", self.symbol, e)
            return None


class CoingeckoApi(CoinRate):
    """Abstracts the coingecko API"""

    api_url = "https://api.coingecko.com"
    path_f = "/api/v3/simple/price?ids={}&vs_currencies={}"

    def __init__(
        self,
        provider: str,
        tid: str,
        vs_currency: str,
        quote_currency: bool = False,
        rate_calculation_method: str = "multiply",
    ):
        self.provider = provider
        self.tid = tid
        self.vs_currency = vs_currency
        self.quote_currency = quote_currency
        self.rate_calculation_method = rate_calculation_method

    def get_path(self):
        return self.path_f.format(self.tid, self.vs_currency)

    async def get_rate(
        self,
        chain_query: Optional[ChainQuery] = None,
        quote_currency_rate: Optional[float] = None,
        quote_symbol: Optional[str] = None,
    ):
        try:
            logger.info("Getting coingecko %s-%s rate", self.tid, self.vs_currency)
            resp = await self._get(self.get_path())
            if resp.is_ok:
                json_data = resp.json
                if (
                    json_data is not None
                    and self.tid in json_data
                    and self.vs_currency in json_data[self.tid]
                ):
                    base_rate = float(json_data[self.tid][self.vs_currency])
                    (rate, output_symbol) = self._calculate_final_rate(
                        self.quote_currency,
                        base_rate,
                        quote_currency_rate,
                        self.rate_calculation_method,
                        self.tid + "-" + self.vs_currency,
                        quote_symbol,
                    )
                    logger.debug("%s %s Rate: %s", self.provider, output_symbol, rate)
                    return rate
                logger.error(
                    "Invalid or missing data in JSON response for %s-%s",
                    self.tid,
                    self.vs_currency,
                )
                return None
        except UnsuccessfulResponse as e:  # pylint: disable=invalid-name
            logger.error("Failed to get rate for coingecko %s: %s", self.tid, e)
            return None


class SundaeswapApi(CoinRate):
    """Abstracts the Sundaeswap API"""

    api_url = "https://stats.sundaeswap.finance"
    path = "/graphql"

    def __init__(
        self,
        provider: str,
        symbol: str,
        quote_currency: bool = False,
        rate_calculation_method: str = "multiply",
    ):
        self.provider = provider
        self.symbol = symbol
        self.quote_currency = quote_currency
        self.rate_calculation_method = rate_calculation_method
        self.query = {
            "query": """
            query searchPools($query: String!) {
              pools(query: $query) {
                ...PoolFragment
              }
            }

            fragment PoolFragment on Pool {
              assetA {
                ...AssetFragment
              }
              assetB {
                ...AssetFragment
              }
              assetLP {
                ...AssetFragment
              }
              fee
              quantityA
              quantityB
              quantityLP
              ident
              assetID
            }

            fragment AssetFragment on Asset {
              assetId
              policyId
              assetName
              decimals
            }
        """,
            "variables": {"query": self.symbol},
            "operationName": "searchPools",
        }

    def get_path(self):
        return self.path

    async def get_rate(
        self,
        chain_query: Optional[ChainQuery] = None,
        quote_currency_rate: Optional[float] = None,
        quote_symbol: Optional[str] = None,
    ):
        try:
            logger.info("Getting Sundaeswap %s rate", self.symbol)
            resp = await self._post(self.get_path(), self.query)
            if resp.is_ok:
                json_data = resp.json
                if (
                    json_data is not None
                    and "data" in json_data
                    and "pools" in json_data["data"]
                    and len(json_data["data"]["pools"]) > 0
                ):
                    quantity_ada = json_data["data"]["pools"][0]["quantityA"]
                    quantity_asset = json_data["data"]["pools"][0]["quantityB"]
                    base_rate = float(quantity_ada) / float(quantity_asset)
                    (rate, output_symbol) = self._calculate_final_rate(
                        self.quote_currency,
                        base_rate,
                        quote_currency_rate,
                        self.rate_calculation_method,
                        self.symbol,
                        quote_symbol,
                    )
                    logger.info("%s %s Rate: %f", self.provider, output_symbol, rate)
                    return rate
                logger.error("Invalid or missing data in JSON response")
                return None
        except UnsuccessfulResponse as e:  # pylint: disable=invalid-name
            logger.error("Failed to get rate for Sundaeswap %s: %s", self.symbol, e)
            return None


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
    ):
        self.provider = provider
        self.token_a = token_a_name
        self.token_b = token_b_name
        self.token_a_decimal = token_a_decimal
        self.token_b_decimal = token_b_decimal
        self.pool_id = pool_id
        self.get_second_pool_price = get_second_pool_price
        self.quote_currency = quote_currency
        self.rate_calculation_method = rate_calculation_method
        self.pool_nft_policy_id = (
            "0be55d262b29f564998ff81efe21bdc0022621c12f15af08d0f2ddb1"
        )
        self.factory_policy_id = (
            "13aa2accf2e1561723aa26871e071fdf32c867cff7e7d50ad470d62f"
        )
        self.factory_asset_name = "4d494e53574150"  # MINSWAP

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
            return  # handle the error as appropriate
        try:
            logger.info("Getting Minswap %s-%s pool value", self.token_a, self.token_b)

            self.kupo_url = chain_query.ogmios_context._kupo_url

            # Pool UTxO
            pool = await self._get_and_validate_pool(self.pool_id)

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
            return rate
        except UnsuccessfulResponse as e:  # pylint: disable=invalid-name
            logger.error(
                "Failed to get rate for Minswap %s-%s: %s",
                self.token_a,
                self.token_b,
                e,
            )
            return None

    def get_blockfrost_symbol(self, asset_a, asset_b) -> str:
        """Ensure that the requested symbol corresponds exactly to the symbol retrieved through the
        on-chain query."""
        if f"{self.token_a}-{self.token_b}" == f"{asset_a}-{asset_b}":
            if self.get_second_pool_price:
                return f"{asset_a}/{asset_b}"
            return f"{asset_b}/{asset_a}"
        raise ValueError(
            f"Symbol does not match the combination of {asset_a}-{asset_b}"
        )

    async def _get_and_validate_pool(self, pool_id):
        """Get and validate pool utxo"""
        pool = await self._get_pool_by_id(pool_id)
        if not self._check_valid_pool_output(pool):
            raise ValueError("Factory token not found in the pool")
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
        error_msg = "Pool must have 1 factory token"
        logger.debug(error_msg)
        return False

    async def _get_pool_addresses(self) -> list[str]:
        """bech32 pool addresses."""
        # Factory to idnetify all differente pool addresses
        # https://cardanosolutions.github.io/kupo/#section/Patterns
        # Polocy ID . AssetName
        nft_factory = f"{self.factory_policy_id}.{self.factory_asset_name}"
        response = await Kupo(self.kupo_url).utxos_kupo(nft_factory)
        return [pool.output.address for pool in response]

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

    async def _get_pool_by_id(self, pool_id: str) -> UTxO:
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
        pool_utxos = await Kupo(self.kupo_url).utxos_kupo(nft)

        if not pool_utxos:
            return None

        # Verify if the UTxO's address belongs to one of the verified pools.
        pool_addresses = await self._get_pool_addresses()

        # Return the first UTxO that matches the address of the pool addresses, if any
        return next(
            (utxo for utxo in pool_utxos if utxo.output.address in pool_addresses), None
        )

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

            # Raise error if any of the asset are found
        if asset_a is None or asset_b is None:
            raise ValueError(
                f"Symbol does not match the combination of {self.token_a}-{self.token_b}",
            )

        if self.get_second_pool_price:
            return f"{asset_a}/{asset_b}"
        return f"{asset_b}/{asset_a}"


class WingridersApi(CoinRate):
    """Abstracts the Wingriders API"""

    api_url = "https://api.mainnet.wingriders.com"
    path = "/graphql"

    def __init__(
        self,
        provider: str,
        symbol: str,
        currency_symbol: str,
        token_name: str,
        quote_currency: bool = False,
        rate_calculation_method: str = "multiply",
    ):
        self.provider = provider
        self.symbol = symbol
        self.asset_id = currency_symbol + token_name
        self.quote_currency = quote_currency
        self.rate_calculation_method = rate_calculation_method
        self.query = {
            "operationName": "AssetsAdaExchangeRates",
            "variables": {},
            "query": """query AssetsAdaExchangeRates {
                                assetsAdaExchangeRates {
                                    ...AssetExchangeRateFragment
                                    __typename
                                }
                            }

                            fragment AssetExchangeRateFragment on AssetExchangeRate {
                                assetId
                                baseAssetId
                                exchangeRate
                                __typename
                        }""",
        }

    def get_path(self):
        return self.path

    async def get_rate(
        self,
        chain_query: Optional[ChainQuery] = None,
        quote_currency_rate: Optional[float] = None,
        quote_symbol: Optional[str] = None,
    ):
        try:
            logger.info("Getting Wingriders %s rate", self.symbol)
            resp = await self._post(self.get_path(), self.query)
            if resp.is_ok:
                json_data = resp.json
                if (
                    json_data is not None
                    and "data" in json_data
                    and "assetsAdaExchangeRates" in json_data["data"]
                ):
                    for asset in json_data["data"]["assetsAdaExchangeRates"]:
                        if asset["assetId"] == self.asset_id:
                            base_rate = float(asset["exchangeRate"])
                            (rate, output_symbol) = self._calculate_final_rate(
                                self.quote_currency,
                                base_rate,
                                quote_currency_rate,
                                self.rate_calculation_method,
                                self.symbol,
                                quote_symbol,
                            )
                            logger.info(
                                "%s %s Rate: %s",
                                self.provider,
                                output_symbol,
                                rate,
                            )
                            return rate
                    logger.debug(
                        "Asset ID not found in response for %s-%s",
                        self.provider,
                        self.symbol,
                    )
                else:
                    logger.error("Invalid or missing JSON data in response")
                return None
        except UnsuccessfulResponse as e:  # pylint: disable=invalid-name
            logger.error("Failed to get rate for Wingriders %s: %s", self.symbol, e)
            return None


class MuesliswapApi(CoinRate):
    """Abstracts the Muesliswap API"""

    api_url = "https://api.muesliswap.com"
    path = "/price?base-policy-id=&base-tokenname=&"

    def __init__(
        self,
        provider: str,
        symbol: str,
        currency_symbol: str,
        token_name: str,
        quote_currency: bool = False,
        rate_calculation_method: str = "multiply",
    ):
        self.provider = provider
        self.symbol = symbol
        self.quote_currency = quote_currency
        self.rate_calculation_method = rate_calculation_method
        self.additional_path = (
            self.path
            + "quote-policy-id="
            + currency_symbol
            + "&quote-tokenname="
            + token_name
        )

    def get_path(self):
        return self.path + self.additional_path

    async def get_rate(
        self,
        chain_query: Optional[ChainQuery] = None,
        quote_currency_rate: Optional[float] = None,
        quote_symbol: Optional[str] = None,
    ):
        try:
            logger.info("Getting Muesliswap %s rate", self.symbol)
            resp = await self._get(self.get_path())
            if resp.is_ok:
                json_data = resp.json
                if json_data is not None and "price" in json_data:
                    base_rate = float(json_data["price"])
                    (rate, output_symbol) = self._calculate_final_rate(
                        self.quote_currency,
                        base_rate,
                        quote_currency_rate,
                        self.rate_calculation_method,
                        self.symbol,
                        quote_symbol,
                    )
                    logger.info("%s %s Rate: %f", self.provider, output_symbol, rate)
                    return rate
                logger.error("JSON data is invalid or missing 'price' key")
                return None
        except UnsuccessfulResponse as e:  # pylint: disable=invalid-name
            logger.error("Failed to get rate for Muesliswap %s: %s", self.symbol, e)
            return None


class VyFiApi(CoinRate):
    """This class encapsulates the interaction with the VyFi Dex
    by utilizing the Blockfrost service."""

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
    ):
        self.provider = provider
        self.pool_tokens = pool_tokens
        self.pool_address = pool_address
        self.minting_a_policy = minting_a_token_policy
        self.minting_b_policy = minting_b_token_policy
        self.get_second_pool_price = get_second_pool_price
        self.quote_currency = quote_currency
        self.rate_calculation_method = rate_calculation_method
        self.min_ada_per_utxo = 2000000  # Min ADA required per UTxO

    async def get_rate(
        self,
        chain_query: Optional[ChainQuery] = None,
        quote_currency_rate: Optional[float] = None,
        quote_symbol: Optional[str] = None,
    ):
        try:
            logger.info("Getting VyFi pool value for tokens: %s", self.pool_tokens)

            if chain_query is None:
                logger.critical("ChainQuery object not found")
                return None

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
                    return None

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
                    return None

                # Adjust tokens amounts by substracting the fees.
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
                    return None

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
                    return None

                # Adjust tokens amounts by substracting the fees.
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
            return rate

        except UnsuccessfulResponse as e:  # pylint: disable=invalid-name
            logger.error("Failed to get rate for VyFi %s: %s", self.pool_tokens, e)
            return None

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
        return None

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
        """Retrive the associated script hash"""
        token_script_hash = ScriptHash(bytes.fromhex(policy_id))
        logger.info(
            "Target script hash for token %s: %s",
            token_name,
            token_script_hash,
        )
        return token_script_hash


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
    ):
        self.provider = provider
        self.network_tokens = network_tokens
        self.network_address = network_address
        self.network_minting_policy = network_minting_policy
        self.quote_currency = quote_currency
        self.rate_calculation_method = rate_calculation_method

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
                return None

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
            return rate

        except UnsuccessfulResponse as e:  # pylint: disable=invalid-name
            logger.error(
                "Failed to get rate for Charli3Api %s: %s", self.network_tokens, e
            )
            return None


class InverseCurrencyRate(CoinRate):
    """handle the inverse of the currency rate"""

    def __init__(
        self,
        provider: str,
        symbol: str,
        quote_currency: bool = True,
        rate_calculation_method: str = "divide",
    ):
        self.provider = provider
        self.symbol = symbol
        self.quote_currency = quote_currency
        self.rate_calculation_method = rate_calculation_method

    async def get_rate(
        self,
        chain_query: ChainQuery = None,
        quote_currency_rate: Optional[float] = None,
        quote_symbol: Optional[str] = None,
    ):
        try:
            logger.info("Getting %s rate", self.symbol)
            if quote_currency_rate is not None:
                (rate, output_symbol) = self._calculate_final_rate(
                    self.quote_currency,
                    base_rate=1,
                    quote_currency_rate=quote_currency_rate,
                    rate_calculation_method=self.rate_calculation_method,
                    base_symbol=self.symbol,
                    quote_symbol=quote_symbol,
                )
                logger.info("%s %s Rate: %s", self.provider, output_symbol, rate)
                return rate
        except UnsuccessfulResponse:
            return None


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


class AggregatedCoinRate:
    """Handles rate review on market"""

    def __init__(
        self,
        quote_currency: bool = False,
        quote_symbol: Optional[str] = None,
        chain_query: ChainQuery = None,
    ):
        self.quote_currency = quote_currency
        self.quote_symbol = quote_symbol
        self.base_data_providers: List[CoinRate] = []
        self.quote_data_providers: List[CoinRate] = []
        self.chain_query = chain_query

    def add_base_data_provider(self, feed_type, provider, pair):
        """add provider to list."""
        self.base_data_providers.append(apiTypes[feed_type](provider, **pair))

    def add_quote_data_provider(self, feed_type, provider, pair):
        """add provider to list."""
        self.quote_data_providers.append(apiTypes[feed_type](provider, **pair))

    async def get_rate_from_providers(
        self,
        providers: List[CoinRate],
        quote_rate: Optional[float] = None,
        conversion_symbol=None,
    ) -> Optional[float]:
        """Get rate from providers.

        Args:
            providers (List[CoinRate]): list of providers
            quote_rate (Optional[float], optional): quote rate. Defaults to None.

        Returns:
            Optional[float]: rate
        """
        rates_to_get = []
        for provider in providers:
            rates_to_get.append(
                provider.get_rate(self.chain_query, quote_rate, conversion_symbol)
            )

        responses = await asyncio.gather(*rates_to_get, return_exceptions=True)

        # Filtering out invalid responses, avoiding null, zero, and instance errors.
        valid_responses = [
            resp
            for resp in responses
            if resp is not None and isinstance(resp, (int, float)) and resp > 0
        ]
        if not valid_responses:
            logger.critical("No data prices are available to estimate the median")
            return None

        result = random_median(valid_responses)
        logger.info("Aggregated rate calculated : %s from %s", result, valid_responses)
        return result

    async def get_aggregated_rate(self):
        """calculate aggregated rate from list of data providers."""

        quote_rate = None
        logger.info("get_aggregated_rate: fetching price from data providers")

        # Fetch Median Quote Rate first if quote_currency is True
        if self.quote_currency:
            logger.info("fetching quote price from data providers")
            quote_rate = await self.get_rate_from_providers(self.quote_data_providers)
            if quote_rate is None:
                logger.error("No valid quote rates available.")

        # Fetch Median Base Rate with quote_rate calculation if quote_currency is enabled
        base_rate = await self.get_rate_from_providers(
            self.base_data_providers, quote_rate, self.quote_symbol
        )

        if base_rate is None:
            logger.error("No valid base rates available.")

        return base_rate
