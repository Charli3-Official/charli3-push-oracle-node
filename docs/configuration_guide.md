# Charli3 Node Operator Backend Configuration Guide

This guide will help you configure the `config.yml` file for the Charli3 Node Operator Backend. The provided `example-config.yml` file contains an example configuration, which you can use as a starting point.

## Configuration Sections

The `config.yml` file contains several sections, each responsible for configuring a specific aspect of the backend. The main sections are:

- Updater
- Node
- ChainQuery
- Rate
- Alerts
- RewardCollection
### NodeSync
```yaml
NodeSync:
  api_url: http://localhost:3000
```
For syncing nodes with the Charli3 DB

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
  oracle_addr: addr_test1wz6jdu4f0eeamgzz2a8wt3eufux33nv6ju35z6r4de5rl0sncyqgh
  c3_token_hash: 436941ead56c61dbf9b92b5f566f7d5b9cac08f8c957f28f0bd60d4b
  c3_token_name: PAYMENTTOKEN
 ```
 Options:

- `signing_key`: The node's signing key file.
- `verification_key`: The node's verification key file.
- `mnemonic`: Your mnemonic phrase for the wallet. (Either mnemonic or keys.)
- `oracle_curr`: The oracle currency script hash.
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
Rate: #Book/USD Feed Config.
  general_base_symbol: BOOK-USD
  general_quote_symbol: ADA-USD

  base_currency:
    dexes:
      - adapter: charli3-dendrite
        asset_a: 51a5e236c4de3af2b8020442e2a26f454fda3b04cb621c1294a0ef34424f4f4b
        asset_b: lovelace
        quote_required: true
        sources:
          - minswapv2
          - vyfi
          - wingriders
          - spectrum
          - sundaeswap
          - sundaeswapv3
          - muesliswap

  quote_currency:
    api_sources:
      - adapter: generic-api
        asset_a: ADA
        asset_b: USDT
        sources:
          - name: xt
            api_url: "https://sapi.xt.com/v4/public/ticker?symbol=ada_usdt"
            json_path: ["result", 0, "c"]
            headers: {}

          - name: gate
            api_url: "https://api.gateio.ws/api2/1/ticker/ada_usdt"
            json_path: ["last"]
            headers: {}

          - name: crypto
            api_url: "https://api.crypto.com/v2/public/get-ticker?instrument_name=ADA_USDT"
            json_path: ["result", "data", 0, "a"]
            headers: {}

          - name: huobi
            api_url: "https://api.huobi.pro/market/trade?symbol=adausdt"
            json_path: ["tick", "data", 0, "price"]
            headers: {}

      - adapter: generic-api
        asset_a: ADA
        asset_b: USD
        sources:
          - name: coinbase
            api_url: "https://api.exchange.coinbase.com/products/ADA-USD/ticker/"
            json_path: ["price"]
            headers: {}

          - name: kraken
            api_url: "https://api.kraken.com/0/public/Ticker?pair=ADAUSD"
            json_path: ["result", "ADAUSD", "o"]
            headers: {}

          - name: btse
            api_url: "https://api.btse.com/spot/api/v3.2/price?symbol=ADA-USD"
            json_path: [0, "lastPrice"]
            headers: {}

          - name: bitfinex
            api_url: "https://api.bitfinex.com/v2/ticker/tADAUSD"
            json_path: [6]
            headers: {}

      - adapter: generic-api
        asset_a: ADA
        asset_b: USDC
        sources:
          - name: bitget
            api_url: "https://api.bitget.com/api/spot/v1/market/ticker?symbol=ADAUSDC_SPBL"
            json_path: ["data", "close"]
            headers: {}

          - name: kucoin
            api_url: "https://api.kucoin.com/api/v1/market/orderbook/level1?symbol=ADA-USDC"
            json_path: ["data", "price"]
            headers: {}

          - name: okx
            api_url: "https://www.okx.com/api/v5/market/ticker?instId=ADA-USDC"
            json_path: ["data", 0, "last"]
            headers: {}

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

### Alerts

The Alerts section allows you to configure the alert system for your node.

Example configuration:

```yaml
Alerts:
  cooldown: 1800  # 30 minutes (Optional)
  thresholds:  # (Optional)
    c3_token_balance: 1000  # in C3 tokens
    ada_balance: 500  # in ADA
    timeout_variance: 105  # percentage
    minimum_data_sources: 3
  notifications:  # at least one notification is required
    - type: slack
      config:
        webhook_url: "{tokenA}/{tokenB}/{tokenC}"
    - type: discord
      config:
        webhook_url: "{WebhookID}/{WebhookToken}"
    - type: telegram
      config:
        bot_token: your_bot_token
        chat_id: your_chat_id
```

Options:

- `cooldown`: Time (in seconds) between repeated alerts of the same type.
- `thresholds`: Customize alert trigger thresholds:
  - `c3_token_balance`: Minimum C3 token balance (in whole tokens)
  - `ada_balance`: Minimum ADA balance (in ADA)
  - `timeout_variance`: Percentage to adjust timeout thresholds
  - `minimum_data_sources`: Minimum number of active data sources
- `notifications`: Configure one or more notification services:
  - `type`: The service type (slack, discord, or telegram)
  - `config`: Service-specific configuration

### RewardCollection

The RewardCollection section allows you to configure automatic reward collection for your node.

Example configuration:

```yaml
RewardCollection:
  destination_address: "addr_test1wqf99gagnjgfamek9v9vyrwulwh64xdnerq9xkvfhwyeu3qdufj2x"
  trigger_amount: 1000  # 1000 C3 tokens
```

Options:

- `destination_address`: The address where collected rewards will be sent
- `trigger_amount`: The amount of C3 tokens that triggers a reward collection

## Configuration Priority

The Charli3 Node Operator Backend supports merging configurations from two files: `config.yml` and `dynamic_config.yml`. Parameters in `config.yml` take precedence over the same parameters in `dynamic_config.yml`. This allows for flexible and dynamic configuration management.

### Merging Configurations

To merge configurations, the backend will load both `config.yml` and `dynamic_config.yml`, with `config.yml` taking precedence. This means that if a parameter is defined in both files, the value from `config.yml` will be used.

### Validation and Warnings

The backend will validate that required parameters are present in at least one of the configuration files. If there are conflicting values between the two files, a warning will be issued, showing which value will be used.

## Final Steps

After updating the `config.yml` file based on your requirements, save the changes and start the Charli3 Node Operator application. Ensure that your application is using the correct `config.yml` file and that it has the appropriate permissions to read the file.

When the application is running, it will utilize the configuration provided in the `config.yml` file to retrieve data from the specified sources, perform any necessary calculations, interact with the Cardano blockchain based on the configured settings, and send alerts according to your specifications.

By following the guidelines provided in this document, you can customize your Charli3 Node Operator application to suit your specific needs and preferences, ensuring a seamless and efficient experience as you work with the Cardano blockchain and its associated assets. The new alert system will keep you informed of critical events, while the automatic reward collection feature will help manage your rewards more efficiently.
