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

## 6. Muesliswap Adapter
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

## 7. InverseCurrencyRate Adapter
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