"""This module contains the functions to load the configuration, setup logging, and setup."""

import logging
import os
from logging.config import dictConfig
from typing import List, Optional, Tuple

import ogmios
from charli3_offchain_core import ChainQuery, Node
from charli3_offchain_core.backend.kupo import KupoContext
from pycardano import (
    Address,
    AssetName,
    BlockFrostChainContext,
    ExtendedSigningKey,
    HDWallet,
    MultiAsset,
    Network,
    OgmiosChainContext,
    PaymentSigningKey,
    PaymentVerificationKey,
    ScriptHash,
    TransactionId,
    TransactionInput,
)

from backend.api import AggregatedCoinRate, NodeSyncApi
from backend.db.crud.feed_crud import feed_crud
from backend.db.database import get_session
from backend.db.models.provider import Provider
from backend.logfiles.logging_config import LEVEL_COLORS, get_log_config
from backend.runner import FeedUpdater


# Setup Logging
def setup_logging(config):
    """Setup the logging configuration based on the specified configuration."""
    dictConfig(get_log_config(config["Updater"]))


original_log_record_factory = logging.getLogRecordFactory()


def record_factory(*args, **kwargs):
    """Factory function for creating log records."""
    record = original_log_record_factory(*args, **kwargs)
    record.level_color = LEVEL_COLORS[record.levelno // 10]
    record.end_color = "\033[0m"
    return record


# Setup Network
def setup_network(config) -> Network:
    """Setup the network based on the specified configuration."""
    network_config = config["ChainQuery"]
    network = (
        Network.TESTNET if network_config["network"] == "TESTNET" else Network.MAINNET
    )
    os.environ["NETWORK"] = "preprod" if network == Network.TESTNET else "mainnet"
    return network


# Setup BlockFrost Context
def setup_blockfrost_context(config, network) -> Optional[BlockFrostChainContext]:
    """Setup the BlockFrost chain context based on the specified configuration."""
    blockfrost_config = config.get("blockfrost")
    if (
        blockfrost_config
        and "project_id" in blockfrost_config
        and blockfrost_config["project_id"]
    ):
        os.environ["PROJECT_ID"] = blockfrost_config["project_id"]
        os.environ["MAX_CALLS"] = str(blockfrost_config.get("max_api_calls", "50000"))
        return BlockFrostChainContext(
            blockfrost_config["project_id"],
            network,
            base_url=blockfrost_config.get("base_url", ""),
        )
    return None


# Setup Ogmios Context
def setup_ogmios_context(config, network) -> Optional[OgmiosChainContext]:
    """Setup the Ogmios chain context based on the specified configuration."""
    ogmios_config = config.get("ogmios")
    if ogmios_config and "ws_url" in ogmios_config and ogmios_config["ws_url"]:
        ogmios_ws_url = ogmios_config["ws_url"]
        kupo_url = ogmios_config.get("kupo_url")
        if ogmios_config.get("pogmios"):
            _, ws_string = ogmios_ws_url.split("ws://")
            ws_url, port = ws_string.split(":")
            return ogmios.OgmiosChainContext(
                host=ws_url, port=int(port), network=network
            )
        return OgmiosChainContext(
            network=network, ws_url=ogmios_ws_url, kupo_url=kupo_url
        )
    return None


def setup_kupo_context(config) -> Optional[KupoContext]:
    """Setup the Kupo context based on ogmios configuration."""
    ogmios_config = config.get("ogmios")
    if ogmios_config and "kupo_url" in ogmios_config and ogmios_config["kupo_url"]:
        return KupoContext(kupo_url=ogmios_config["kupo_url"])


# Setup Chain Query
def setup_chain_query(config, network) -> Optional[ChainQuery]:
    """Setup the chain query based on the specified configuration."""
    chain_query_config = config.get("ChainQuery")
    node_config = config.get("Node")
    if chain_query_config:
        return ChainQuery(
            blockfrost_context=setup_blockfrost_context(chain_query_config, network),
            ogmios_context=setup_ogmios_context(chain_query_config, network),
            oracle_address=node_config["oracle_address"],
            kupo_context=setup_kupo_context(chain_query_config),
        )
    return None


async def ensure_feed_in_db(
    feed_address,
    title,
    aggstate_nft,
    oracle_nft,
    node_nft,
    reward_nft,
    oracle_currency,
    db_session,
):
    """Ensure that the feed address is in the database."""
    feed = await feed_crud.get_feed_by_address(
        db_session=db_session, address=feed_address
    )
    if not feed:
        obj_in = {
            "feed_address": feed_address,
            "title": title,
            "aggstate_nft": aggstate_nft,
            "oracle_nft": oracle_nft,
            "node_nft": node_nft,
            "reward_nft": reward_nft,
            "oracle_currency": oracle_currency,
        }
        feed = await feed_crud.create(
            db_session=db_session,
            obj_in=obj_in,
        )
    return feed


# Setup Node and Chain Query
async def setup_node_and_chain_query(config):
    """Setup the node based on the specified configuration."""
    node_config = config.get("Node")
    chain_query_config = config.get("ChainQuery")

    network = Network.TESTNET
    if node_config:
        if chain_query_config["network"] == "TESTNET":
            network = Network.TESTNET
            os.environ["NETWORK"] = "preprod"
        elif chain_query_config["network"] == "MAINNET":
            network = Network.MAINNET
            os.environ["NETWORK"] = "mainnet"

        chain_query = setup_chain_query(config, network)

        oracle_nft_hash = ScriptHash.from_primitive(node_config["oracle_curr"])

        node_nft = MultiAsset.from_primitive(
            {oracle_nft_hash.payload: {b"NodeFeed": 1}}
        )
        oracle_nft = MultiAsset.from_primitive(
            {oracle_nft_hash.payload: {b"OracleFeed": 1}}
        )
        aggstate_nft = MultiAsset.from_primitive(
            {oracle_nft_hash.payload: {b"AggState": 1}}
        )
        reward_nft = MultiAsset.from_primitive(
            {oracle_nft_hash.payload: {b"Reward": 1}}
        )

        if "mnemonic" in node_config and node_config["mnemonic"]:
            hdwallet = HDWallet.from_mnemonic(node_config["mnemonic"])
            hdwallet_spend = hdwallet.derive_from_path("m/1852'/1815'/0'/0/0")
            spend_public_key = hdwallet_spend.public_key
            node_vk = PaymentVerificationKey.from_primitive(spend_public_key)
            node_sk = ExtendedSigningKey.from_hdwallet(hdwallet_spend)

        elif node_config["signing_key"] and node_config["verification_key"]:
            node_sk = PaymentSigningKey.load(node_config["signing_key"])
            node_vk = PaymentVerificationKey.load(node_config["verification_key"])

        if (
            "reference_script_input" in node_config
            and node_config["reference_script_input"]
        ):
            tx_id_hex, index = node_config["reference_script_input"].split("#")
            tx_id = TransactionId(bytes.fromhex(tx_id_hex))
            index = int(index)
            reference_script_input = TransactionInput(tx_id, index)
        else:
            reference_script_input = None

        if (
            "c3_oracle_rate_address" in node_config
            and node_config["c3_oracle_rate_address"]
        ):
            c3_oracle_rate_address = Address.from_primitive(
                node_config["c3_oracle_rate_address"]
            )
        else:
            c3_oracle_rate_address = None

        if "c3_oracle_nft_hash" in node_config and node_config["c3_oracle_nft_hash"]:
            c3_oracle_nft_hash = ScriptHash.from_primitive(
                node_config["c3_oracle_nft_hash"]
            )
        else:
            c3_oracle_nft_hash = None

        if "c3_oracle_nft_name" in node_config and node_config["c3_oracle_nft_name"]:
            c3_oracle_nft_name = node_config["c3_oracle_nft_name"]
        else:
            c3_oracle_nft_name = None

        if c3_oracle_nft_hash and c3_oracle_nft_name:
            c3_oracle_nft = MultiAsset.from_primitive(
                {c3_oracle_nft_hash.payload: {bytes(c3_oracle_nft_name, "utf-8"): 1}}
            )
        else:
            c3_oracle_nft = None

        node = Node(
            network,
            chain_query,
            node_sk,
            node_vk,
            node_nft,
            aggstate_nft,
            oracle_nft,
            reward_nft,
            Address.from_primitive(node_config["oracle_address"]),
            ScriptHash.from_primitive(node_config["c3_token_hash"]),
            AssetName(bytes(node_config["c3_token_name"], "utf-8")),
            reference_script_input,
            oracle_rate_addr=c3_oracle_rate_address,
            oracle_rate_nft=c3_oracle_nft,
        )

        async with get_session() as db_session:
            base_symbol = config.get("Rate").get("general_base_symbol", None)
            feed = await ensure_feed_in_db(
                node_config["oracle_address"],
                base_symbol,
                str(aggstate_nft),
                str(oracle_nft),
                str(node_nft),
                str(reward_nft),
                str(oracle_nft_hash),
                db_session,
            )
        return node, chain_query, feed
    return None


# Setup Aggregated Rate
async def setup_aggregated_coin_rate(
    config, chain_query, feed_id
) -> Tuple[AggregatedCoinRate, List[Provider]]:
    """
    Initializes and returns an AggregatedCoinRate instance based on the application configuration.
    :param config: The loaded application configuration.
    :param chain_query: An instance of ChainQuery.
    :return: An instance of AggregatedCoinRate.
    """
    providers = []
    async with get_session() as db_session:
        # Initialize AggregatedCoinRate instance
        if "quote_currency" in config["Rate"] and config["Rate"]["quote_currency"]:
            quote_symbol = config.get("Rate").get("general_quote_symbol", None)
            rate_class = AggregatedCoinRate(
                quote_currency=True,
                quote_symbol=quote_symbol,
                chain_query=chain_query,
                feed_id=feed_id,
                slack_alerts=config.get("SlackAlerts", {}),
            )
        else:
            rate_class = AggregatedCoinRate(
                quote_currency=False,
                chain_query=chain_query,
                feed_id=feed_id,
                slack_alerts=config.get("SlackAlerts", {}),
            )

        # Add quote data providers
        if rate_class.quote_currency:
            for provider_key, provider_value in config["Rate"][
                "quote_currency"
            ].items():
                feed_type = provider_value["type"]
                del provider_value[
                    "type"
                ]  # Assuming 'provider_value' includes 'feed_id'
                provider = await rate_class.add_quote_data_provider(
                    feed_type,
                    provider_key,
                    provider_value,
                    db_session,
                )
                providers.append(provider)

        # Add base data providers
        for provider_key, provider_value in config["Rate"]["base_currency"].items():
            feed_type = provider_value["type"]
            del provider_value["type"]  # Assuming 'provider_value' includes 'feed_id'
            provider = await rate_class.add_base_data_provider(
                feed_type,
                provider_key,
                provider_value,
                db_session,
            )
            providers.append(provider)

    return rate_class, providers


# Setup Feed Updater
async def setup_feed_updater(config) -> Optional[FeedUpdater]:
    """Setup the feed updater based on the specified configuration."""
    updater_config = config.get("Updater")
    node_config = config.get("Node")
    node, chainquery, feed = await setup_node_and_chain_query(config)
    aggregated_rate, providers = await setup_aggregated_coin_rate(
        config, chainquery, feed.id
    )
    if updater_config:
        if "node_sync_api" in node_config:
            node_sync_api = NodeSyncApi(node_config.get("node_sync_api", None))
            await node_sync_api.report_initialization(feed, node, providers)
        else:
            node_sync_api = None

        return FeedUpdater(
            update_inter=int(updater_config["update_inter"]),
            percent_resolution=int(updater_config["percent_resolution"]),
            reward_collection_trigger=node_config.get("reward_collection_trigger", 0),
            reward_destination_address=node_config.get(
                "reward_destination_address", None
            ),
            node=node,
            rate=aggregated_rate,
            context=chainquery,
            feed_id=feed.id,
            node_sync_api=node_sync_api,
        )
    return None
