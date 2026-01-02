# Charli3 Node Operator Backend
This project provides a backend for Node Operators using the Charli3 Oracle. It is designed to fetch, aggregate and update price data for specified assets. The script can be configured with a custom config.yaml file and it utilizes the pycardano library for Cardano blockchain interactions.

**Note**: The following demo was tested with Cardano-node v8.9.3, Ogmios v6.4.0, and Kupo v2.8.0. Older versions may not work properly.

## Getting Started
### Dependencies
This project uses Poetry to manage dependencies. If you don't have Poetry installed, you can install it by following the instructions at [Poetry documentation](https://python-poetry.org/docs/).

To install the required Python packages, run:

```
poetry install
```
Next, you will need to create a config.yml file containing the necessary configuration settings. You can use the provided [example-config.yml](example-config.yml) as a starting point.

## Running the Backend
### Locally
To run the backend locally, execute the main.py script inside the Poetry environment:

```
poetry run python main.py
```
You can also pass a custom configuration file by using the -c or --configfile command line option:

```
poetry run python main.py -c your_config_file.yml
```
### Using Docker
First, build the Docker image:
```
docker build -t charli3-node-operator-backend .
```
Then, run the Docker container using Docker Compose:

```
docker-compose up -d
```

## Configuration
The backend can be configured using a config.yml file. This file allows you to customize various settings such as:

- ChainQuery configurations (BlockFrost and Ogmios)
- Node and oracle settings (addresses, keys, mnemonics, etc.)
- Data providers for base and quote currency rates

Refer to the [example-config.yml](example-config.yml) file for an example configuration.

For detailed information about customizing the `config.yml` file, including ChainQuery configurations, node and oracle settings, and data providers for base and quote currency rates, please refer to our comprehensive [Configuration Guide](docs/configuration_guide.md).

For more details about the different adapters available, their usage, and configuration options, please refer to the [Adapters Guide](docs/adapters_guide.md). This guide provides comprehensive information on how to effectively utilize each adapter in your currency rate configuration.

## Functionality
The Charli3 Node Operator Backend provides the following functionality:

- Interacting with the Cardano blockchain using the `ChainQuery` class
- Managing nodes, aggregating states, and oracle NFTs with the `Node` class
- Updating the aggregated coin rate with the `FeedUpdater` class
- Interfacing with various data providers for base and quote currency rates using the `AggregatedCoinRate` class

## Testing
This project uses Pytest for testing. To run the tests, execute the following command:
```
poetry run pytest
```

## License

This repository is licensed under the **MIT license**.

### License Rationale

Charli3 uses a combination of OSI-approved open-source licenses, primarily AGPL-3.0 and MIT, depending on the role of each repository within the ecosystem.
Repositories that implement core or protocol-critical logic are licensed under AGPL-3.0 to ensure that improvements and modifications remain transparent and benefit the entire ecosystem, including node operators, developers, and token holders, while maintaining full OSI compliance. This may include both on-chain and select off-chain components where protocol logic and token usage are integral.

Repositories focused on tooling, SDKs, and supporting components are typically licensed under the MIT License to promote broad adoption, flexibility, and ease of integration.

AGPL-3.0 is applied where reciprocal openness is important to protect shared protocol infrastructure, while MIT is used where permissiveness and developer flexibility are the primary goals.

Please refer to each repository’s [LICENSE](LICENSE) file for the specific terms that apply.


## Official Deployments

Charli3 maintains and supports only official deployments that use the $C3 token and unmodified protocol economics.
