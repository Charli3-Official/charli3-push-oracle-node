# Charli3 Node Operator Backend Configuration Guide

This guide will help you configure the `config.yml` file for the Charli3 Node Operator Backend. The provided `example-config.yml` file contains an example configuration, which you can use as a starting point.

## Configuration Sections

The `config.yml` file contains several sections, each responsible for configuring a specific aspect of the backend. The main sections are:

- Updater
- Node
- ChainQuery
- Rate

### Updater

The Updater section is responsible for configuring the update interval, logging verbosity, and percent resolution for the backend.

Example configuration:

```yaml
Updater:
  update_inter: 180
  verbosity: INFO
  percent_resolution: 10000
```
Options:

- `update_inter`: The interval (in seconds) between updates.
- `verbosity`: Logging verbosity level (e.g., INFO, DEBUG, WARNING, ERROR, CRITICAL).
- `percent_resolution`: The percent resolution for updating the aggregated coin rate.

### Node

The Node section is responsible for configuring node-related settings such as keys, oracle address, token settings, and NFTs.

Example configuration:

```yaml
Node:
  signing_key: node3.skey
  verification_key: node3.vkey
  mnemonic: your_mnemonic_phrase_here
  oracle_curr: 2e527c8e42d0f28fd3f4025f60c0a89bc5815c8e2efc3fb973e3fc20
  node_nft: NodeFeed
  aggstate_nft: AggState
  oracle_nft: OracleFeed
  oracle_addr: addr_test1wz6jdu4f0eeamgzz2a8wt3eufux33nv6ju35z6r4de5rl0sncyqgh
  c3_token_hash: 436941ead56c61dbf9b92b5f566f7d5b9cac08f8c957f28f0bd60d4b
  c3_token_name: PAYMENTTOKEN
 ```
 Options:

- `signing_key`: The node's signing key file.
- `verification_key`: The node's verification key file.
- `mnemonic`: Your mnemonic phrase for the wallet. (Either mnemonic or keys.)
- `oracle_curr`: The oracle currency script hash.
- `node_nft`: The node NFT name.
- `aggstate_nft`: The aggregated state NFT name.
- `oracle_nft`: The oracle NFT name.
- `oracle_addr`: The oracle address.
- `c3_token_hash`: The C3 token hash.
- `c3_token_name`: The C3 token name.
 
 ### ChainQuery

The ChainQuery section is responsible for configuring ChainQuery settings, such as network type, BlockFrost settings, and Ogmios settings and contains settings related to the blockchain querying process. It also now supports an optional Kupo configuration.

It can work with any one option from blockfrost and ogmios. If both enable then querying part will be done by blockfrost and ogmios will be used to tx submission.

When the optional Kupo configuration is provided in Ogmios configuration, the UTxO query will be done by Kupo.

Example configuration:

```yaml
ChainQuery:
  network: TESTNET
  blockfrost:
    base_url: https://cardano-preprod.blockfrost.io/api
    project_id: preprodVPAHdGNLvQtM3Ppkxtvd2oEVhHFxZ6MD
  ogmios:
    ws_url:  wss://ogmios-preprod-api-charli3-49bb04.us1.demeter.run
    kupo_url: https://kupo-url   # optional
```
Options:

- `network`: The network type (e.g., TESTNET, MAINNET).
- `blockfrost`: BlockFrost settings.
  - `base_url`: The BlockFrost base URL.
  - `project_id`: The BlockFrost project ID.
- `ogmios`: Ogmios settings.
  - `ws_url`: The Ogmios WebSocket URL.
  - `kupo_url`: The optional Kupo URL. If provided, UTXO query will be handled by Kupo.

### Rate

The Rate section is responsible for configuring the base and quote currency settings for various exchanges and DEXes.

For more details about the different adapters available, their usage, and configuration options, please refer to the [Adapters Guide](adapters_guide.md). This guide provides comprehensive information on how to effectively utilize each adapter in your currency rate configuration.

Example configuration:
```yaml
Rate: #SHENUSD Feed Config.
  base_currency:
    sundaeswap:
      type: sundaeswap
      symbol: Shen
      quote_currency: True
    minswap:
      type: minswap
      symbol: SHEN/ADA
      currency_symbol: 8db269c3ec630e06ae29f74bc39edd1f87c819f1056206e879a1cd61
      token_name: 5368656e4d6963726f555344
      quote_currency: True
    muesliswap:
      type: muesliswap
      symbol: SHEN/ADA
      currency_symbol: 8db269c3ec630e06ae29f74bc39edd1f87c819f1056206e879a1cd61
      token_name: 5368656e4d6963726f555344
      quote_currency: True
    bitrue:
      type: generic
      symbol: SHENUSDT
      api_url: https://openapi.bitrue.com
      path: /api/v1/ticker/price?symbol=shenusdt
      json_path: ["price"]
      key: {}
  quote_currency:
    binance:
      type: binance
      symbol: ADAUSDT
    kucoin:
      type: generic
      symbol: ADA-USDT
      api_url: https://api.kucoin.com
      path: /api/v1/prices?currencies=ADA
      json_path: ["data","ADA"]
      key: {}
    kraken:
      type: generic
      symbol: ADAUSD
      api_url: https://api.kraken.com
      path: /0/public/Ticker?pair=ADAUSD
      json_path: ["result","ADAUSD","o"]
      key: {}
    bitrue:
      type: generic
      symbol: ADAUSDT
      api_url: https://openapi.bitrue.com
      path: /api/v1/ticker/price?symbol=adausdt
      json_path: ["price"]
      key: {}
    coinbase:
      type: generic
      symbol: ADA-USD
      api_url: https://api.exchange.coinbase.com
      path: /products/ADA-USD/ticker/
      json_path: ["price"]
      key: {}

```
Options:

- `base_currency`: Configure base currency settings for each exchange or DEX.
  - `type`: The type of exchange or DEX (e.g., sundaeswap, minswap, muesliswap, generic).
  - `symbol`: The trading pair symbol.
  - `currency_symbol`: (Optional) The currency symbol for custom tokens.
  - `token_name`: (Optional) The token name for custom tokens.
  - `api_url`: (Optional) The API URL for generic exchanges.
  - `path`: (Optional) The API path for generic exchanges.
  - `json_path`: (Optional) The JSON path to extract the price data for generic exchanges.
  - `key`: (Optional) API key for the exchange.
  - `quote_currency`: (Optional) Set to True for quote currency settings.

- `quote_currency`: Configure quote currency settings for each exchange.
  - Options are the same as for `base_currency`.

## Final Steps

After updating the `config.yml` file based on your requirements, save the changes and start the Charli3 Node Operator application. Ensure that your application is using the correct `config.yml` file and that it has the appropriate permissions to read the file.

When the application is running, it will utilize the configuration provided in the `config.yml` file to retrieve data from the specified sources, perform any necessary calculations, and interact with the Cardano blockchain based on the configured settings.

By following the guidelines provided in this document, you can customize your Charli3 Node Operator application to suit your specific needs and preferences, ensuring a seamless and efficient experience as you work with the Cardano blockchain and its associated assets.
