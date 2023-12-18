# Adapters Configuration

The adapter classes facilitate interaction with various exchange APIs to extract the required data. Here's how to configure each of the adapter types:

## 1. Generic Adapter
The Generic adapter is a flexible class designed to interact with various APIs that do not have a specific adapter.

Configuration for Generic:

``` yaml
bitrue:
  type: generic
  symbol: SHENUSDT
  api_url: https://openapi.bitrue.com
  path: /api/v1/ticker/price?symbol=shenusdt
  json_path: ["price"]
  key: {}
  quote_currency: True
  rate_calculation_method: "multiply"
```

Options:
- type: Should be set to "generic".
- symbol: The trading pair symbol.
- api_url: The API URL for the exchange.
- path: The API path for the request.
- json_path: The JSON path to extract the price data.
- key: (Optional) API key for the exchange.
- token: (Optional) Bearer token for APIs requiring token-based authentication.
- quote_currency: (Optional) If set to True, this tells the system that this configuration is for the quote currency. Defaults to False.
- rate_calculation_method: (Optional) The method to use for rate calculation. Options are "multiply" and "divide". Defaults to "multiply".

**Token-based Authentication Support**

Some APIs require a token for authentication. The Generic class now supports token-based authentication. You can add your token to the configuration under each exchange's or DEX's settings.

``` yaml
Rate: 
  base_currency:
    binance:
      type: generic
      symbol: BTCUSDT
      api_url: https://api.binance.com
      path: /api/v3/ticker/price
      json_path: ["price"]
      key: {}
      quote_currency: True
      rate_calculation_method: "multiply"
      token: your_bearer_token_here  # Add your token here
  # ...
```

Options:
- token: (Optional) Your authentication token for the API. If the API requires token-based authentication, include it here as a string. The Generic class will include it in the header of the HTTP request as a Bearer token.

## 2. Binance Adapter
The Binance adapter is specifically designed to interact with the Binance exchange API. The Binance API returns the average price for a specified symbol.

Configuration for Binance:

``` yaml
binance:
  type: binance
  symbol: ADAUSDT
  quote_currency: True
  rate_calculation_method: "multiply"
```
Options:
- type: Should be set to "binance".
- symbol: The trading pair symbol.
- quote_currency: (Optional) If set to True, this tells the system that this configuration is for the quote currency. Defaults to False.
- rate_calculation_method: (Optional) The method to use for rate calculation. Options are "multiply" and "divide". Defaults to "multiply".

## 3. Coingecko Adapter
The Coingecko adapter uses the Coingecko API to fetch currency exchange rates.

Here's an example of how to configure the Coingecko adapter:

``` yaml
coingecko:
  type: coingecko
  tid: bitcoin
  vs_currency: usd
  quote_currency: True
```
The Coingecko adapter configuration options:

- type: The adapter type. For the Coingecko adapter, this should be coingecko.
- tid: The id of the token to get the price for. This should be the id used by Coingecko. For example, for Bitcoin, use bitcoin.
- vs_currency: The currency in which you want the price. This should be the id used by Coingecko. For example, for US Dollars, use usd.
- quote_currency: (Optional) If set to True, this tells the system that this configuration is for the quote currency. Defaults to False.
- rate_calculation_method: (Optional) The method to use for rate calculation. Options are "multiply" and "divide". Defaults to "multiply".
  
Note: The Coingecko API provides a list of token ids and currency ids you can use. Visit Coingecko API for more information.

## 4.  Sundaeswap Adapter
The Sundaeswap adapter is specifically designed to interact with the Sundaeswap exchange API.

Configuration for Sundaeswap:
``` yaml
sundaeswap:
  type: sundaeswap
  symbol: Shen
  quote_currency: True
```
Options:
- type: Should be set to "sundaeswap".
- symbol: The trading pair symbol.
- quote_currency: (Optional) If set to True, this tells the system that this configuration is for the quote currency. Defaults to False.
- rate_calculation_method: (Optional) The method to use for rate calculation. Options are "multiply" and "divide". Defaults to "multiply".

## 5. Minswap Adapter
The Minswap adapter is specifically designed to interact with the Minswap exchange API.

Configuration for Minswap:

``` yaml
minswap:
  type: minswap
  symbol: SHEN/ADA
  currency_symbol: 8db269c3ec630e06ae29f74bc39edd1f87c819f1056206e879a1cd61
  token_name: 5368656e4d6963726f555344
  quote_currency: True
```
Options:
- type: Should be set to "minswap".
- symbol: The trading pair symbol.
- currency_symbol: The currency symbol for custom tokens.
- token_name: The token name for custom tokens.
- quote_currency: (Optional) Set to True for quote currency settings.
- rate_calculation_method: (Optional) The method to use for rate calculation. Options are "multiply" and "divide". Defaults to "multiply".

## 6. VyFi Adapter
The VyFi adapter is specifically designed to interact with the VyFi Dex on Cardano.

Configuration for VyFi:

``` yaml
    vyfi:
      type: vyfi
      pool_tokens: ADA-SHEN
      pool_address: addr1z8q336qgth58526mgr72svdlcqvs2jrkxem3thxnuqw4efk08470jem2z3k5yap4fddtxvykxxv2tmr83x06vklv5vys3jhn6c
      minting_a_token_policy:
      minting_b_token_policy: 8db269c3ec630e06ae29f74bc39edd1f87c819f1056206e879a1cd61
      get_second_pool_price: False
```
Options:
- type: Set this value to "vyfi".
- pool_tokens: Indicates the trading pair symbol. Asset arrangement in the pair follows the alphabetical order of their hashes, with Asset A having the preceding hash in a sorted list. Exceptionally, 'lovelace' (Cardano's native currency) always occupies the Asset A position, regardless of its hash.
- pool_address: Identifies the specific liquidity pool's location. Essential for pinpointing the correct UTxO holding the asset pair. It enables accurate data retrieval, including bar fees and liquidity specifics (datum's UTxO)
- minting_a_token_policy (Optional): Minting policy of the asset A, empty if ADA used.
- minting_b_token_policy (Optional): Minting policy of the asset B.
- get_second_pool_price (Optional): In a trading pool like ADA-SHEN, setting this to True yields the ADA/SHEN rate; otherwise, it provides the SHEN/ADA rate.
- quote_currency (Optional): Defaulted to True, this option is for quote currency configurations.
- rate_calculation_method: (Optional) The method to use for rate calculation. Options are "multiply" and "divide". Defaults to "multiply".

Note: In exchange rate calculations for pools like ADA-SHEN, the code identifies the UTxO containing both assets and adjusts the amounts by deducting bar fees from the UTxO's datum. For lovelace transactions, an additional 2 ADA (the minimum ADA per UTxO) is subtracted. The exchange rate is then calculated by dividing these adjusted amounts. Ensure that the necessary assets are defined in both `mainnet_policy_id` and `mainnet_asset_name` for accurate computation.

## 7. Muesliswap Adapter
The Muesliswap adapter is specifically designed to interact with the Muesliswap exchange API.

Configuration for Muesliswap:
``` yaml
muesliswap:
    type: muesliswap
    symbol: SHEN/ADA
    currency_symbol: 8db269c3ec630e06ae29f74bc39edd1f87c819f1056206e879a1cd61
    token_name: 5368656e4d6963726f555344
    quote_currency: True
```
Options:
- type: Should be set to "muesliswap".
- symbol: The trading pair symbol.
- currency_symbol: The currency symbol for custom tokens.
- token_name: The token name for custom tokens.
- quote_currency: (Optional) Set to True for quote currency settings.
- rate_calculation_method: (Optional) The method to use for rate calculation. Options are "multiply" and "divide". Defaults to "multiply".

## 8. Charli3 Adapter
The Charli3 adapter's purpose is to facilitate the conversion between a supported asset pair in the Charli3 protocol and other existing asset pairs. For instance, if the C3 Network pair A/B exists and the objective is to integrate a new network A/C, but more data is available for the pair B/C from different sources, then combining the A/B network data with the readily available B/C data effectively computes the A/C pair

Configuration for charli3:
``` yaml
charli3:
  type: charli3
  network_tokens: ADA-USD
  network_address: addr1wyd8cezjr0gcf8nfxuc9trd4hs7ec520jmkwkqzywx6l5jg0al0ya
  network_minting_policy: 3d0d75aad1eb32f0ce78fb1ebc101b6b51de5d8f13c12daa88017624
```
Options:
- type: Should be set to "charli3".
- network_tokens: The trading pair symbol.
- network_address: C3 Network address
- network_minting_policy: C3 Network minting policy
- quote_currency: (Optional) Set to True for quote currency settings.
- rate_calculation_method: (Optional) The method to use for rate calculation. Options are "multiply" and "divide". Defaults to "multiply".

## 9. InverseCurrencyRate Adapter
The InverseCurrencyRate adapter is a unique type of adapter designed to calculate the inverse of a given currency rate. It doesn't make any API calls to retrieve data; instead, it inverses the rate that is already retrieved from a different source.

This adapter is only applicable in the base currency configuration, and there should be only one instance of the InverseCurrencyRate adapter in the base currency configuration. The configuration for the quote currency will provide the rate to be inverted.

Here's an example of how to configure the InverseCurrencyRate adapter:

``` yaml
base_currency:
  inverseRate:
    type: inverse
    symbol: BTC/USD
    quote_currency: True
    rate_calculation_method: "divide"
```
The InverseCurrencyRate adapter configuration options:
- type: The adapter type. For the InverseCurrencyRate adapter, this should be inverse.
- symbol: The symbol of the currency pair for which the inverse rate is required. For example, if you have the rate for BTC to USD but you want the rate for USD to BTC, use BTC/USD.
- quote_currency: If set to True, this tells the system that this configuration is for the quote currency. Defaults to True.
- rate_calculation_method: (Optional) The method to use for rate calculation. Options are "multiply" and "divide". Defaults to "divide". 
    
Note: For the InverseCurrencyRate adapter, "divide" is typically used to achieve the inversion of the rate.

The InverseCurrencyRate adapter is particularly useful when you have an API that provides the rate in one direction (e.g., BTC to USD), but you need the rate in the other direction (e.g., USD to BTC). Instead of making an additional API call or finding another source for this rate, you can use the InverseCurrencyRate adapter to calculate it based on the rate you already have.
