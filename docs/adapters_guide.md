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
The Minswap adapter is specifically designed to interact with the Minswap DEX on Cardano.

Configuration for Minswap:

``` yaml
minswap:
  type: minswap
  pool_tokens: ADA-SHEN
  pool_id: 53225313968e796f2c1e0b57540a13c3b81e06e2ed2637ac1ea9b9f4e27e3dc4
  get_second_pool_price: False
  quote_currency: True
```
Options:
- type: Should be set to "minswap".
- pool_tokens: This parameter represents the trading pair symbol and should reflect the assets' order as held in the liquidity pool. When determining the sequence of assets (Asset A and Asset B) within the pair, the assets are arranged alphabetically by their asset hashes—Asset A is the one with the hash that precedes Asset B in a sorted list. However, there is a notable exception to this rule: when the pair includes Cardano's native currency ('lovelace'), it will invariably assume the position of Asset A, regardless of its hash in comparison to the other asset in the pool.
- pool_id: This is the unique identifier associated with a specific liquidity pool. It is used to precisely distinguish the pool that contains the pair of assets you intend to interact with. The `pool_id` is essential when querying for pool-specific data, such as exchange rates, liquidity depth, and transaction history.
- get_second_pool_price (Optional): When retrieving the price from a liquidity pool, two numerical values are returned, both expressed as `Decimal` types for precision. The first value represents the cost of purchasing one unit of Token B using Token A as the currency (commonly referred to as the "buy price" of Token B). Conversely, the second value indicates the cost of buying one unit of Token A using Token B (the "buy price" of Token A). For instance, in an ADA-SHEN pool, if the returned values are (X, Y), X would be the SHEN/ADA price, and Y would be the ADA/SHEN price. The `get_second_pool_price` option allows users to select which of these two prices to work with. This selection is typically based on whether you need the base price (the first value) or the quote price (the second value) for your calculations or display purposes.
- rate_calculation_method: (Optional) The method to use for rate calculation. Options are "multiply" and "divide". Defaults to "multiply".
- quote_currency: (Optional) Set to True for quote currency settings.

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
## 10. LP Token Adapter

The LP Token Adapter prices DEX liquidity provider (LP) tokens using on-chain Net Asset Value (NAV) calculation. This adapter is specifically designed to price LP tokens from decentralized exchanges on Cardano.

### How It Works

LP tokens represent a share of a liquidity pool. The adapter calculates their value using on-chain data from the pool state:

**Formula for ADA-paired pools:**
```
LP Token Price (in ADA) = (Total ADA in Pool × 2) / Total LP Tokens Minted
```

This NAV-based approach:
- Uses only on-chain data (pool reserves, LP supply)
- Avoids market manipulation risks from low liquidity LP token markets
- Works even when LP tokens themselves have no direct trading pairs
- Provides accurate pricing based on the underlying pool composition

### Configuration

Configuration for LP Token Adapter:

```yaml
base_currency:
  lp_token:
    - adapter: "lp_token"
      lp_token_id: "full_policy_id_and_asset_name_in_hex"  # Full LP token ID
      pool_dex: "vyfi"  # DEX that issued this LP token
      sources: ["vyfi"]  # Optional: multiple sources for aggregation
      quote_required: false  # Set to true if pricing in quote currency
      quote_calc_method: multiply  # multiply or divide
```

### Configuration Options

- **adapter**: Should be set to `"lp_token"`.
- **lp_token_id** (required): Full token identifier (policy_id + asset_name in hex). This is the complete hex representation of the LP token you want to price.
- **pool_dex** (required): DEX name that issued this LP token. Supported values:
  - `"vyfi"` - VyFi DEX
  - `"minswapv2"` - MinswapV2 DEX
  - `"spectrum"` - Spectrum DEX
- **sources** (optional): List of DEX names to query. Defaults to `[pool_dex]`. Can include multiple DEXes for aggregation if the same LP token exists on multiple platforms.
- **quote_required** (optional): If set to True, the LP token price will be converted using the quote currency rate. Defaults to False.
- **quote_calc_method** (optional): The method to use for quote currency conversion. Options are "multiply" and "divide". Defaults to "multiply".

### Supported DEXes

- **VyFi** ✅ Fully supported
- **MinswapV2** ✅ Fully supported
- **Spectrum** ✅ Fully supported

### Important Notes

1. **Different LP tokens per DEX**: Each DEX issues its own unique LP token for the same trading pair
   - VyFi ADA/USDC LP token ≠ Minswap ADA/USDC LP token
   - They have different prices based on their respective pool reserves and LP token supplies
   - You must specify the exact LP token ID and the DEX that issued it

2. **ADA-paired pools only**: Currently, the adapter only supports pools paired with ADA (lovelace). Pools with other base assets (e.g., USDC/USDT) are not yet supported.

3. **No market price**: LP token price is derived from the pool's underlying composition, not from trading activity of the LP token itself. This makes it resistant to manipulation and always reflects the true value of the pool shares.

4. **Finding LP Token IDs**: You can find LP token IDs by:
   - Querying the pool directly on-chain
   - Using block explorers (e.g., CardanoScan, Cexplorer)
   - Checking the DEX's documentation or API

### Example Use Cases

**Pricing a single DEX's LP token:**
```yaml
base_currency:
  lp_token:
    - adapter: "lp_token"
      lp_token_id: "4086577ed57c514f8e29b78f42ef4f379363355a3b65b9a032ee30c9_lp_vyfi_ada_usdc"
      pool_dex: "vyfi"
      sources: ["vyfi"]
```

**Pricing multiple different LP tokens (different DEXes):**
```yaml
base_currency:
  lp_token:
    # VyFi ADA/USDC LP token
    - adapter: "lp_token"
      lp_token_id: "vyfi_lp_token_id_in_hex"
      pool_dex: "vyfi"
      sources: ["vyfi"]

    # Minswap ADA/USDC LP token (different from VyFi's)
    - adapter: "lp_token"
      lp_token_id: "minswap_lp_token_id_in_hex"
      pool_dex: "minswapv2"
      sources: ["minswapv2"]
```

**Using quote currency conversion:**
```yaml
base_currency:
  lp_token:
    - adapter: "lp_token"
      lp_token_id: "lp_token_id_in_hex"
      pool_dex: "vyfi"
      quote_required: true  # Convert LP price to quote currency
      quote_calc_method: multiply

quote_currency:
  # Define ADA/USD rate sources here
  api_sources:
    - adapter: generic-api
      # ... ADA/USD price sources
```
