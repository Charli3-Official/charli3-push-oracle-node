"""This module contains the functions to load the configuration, setup logging, and setup."""

import logging
import os
from logging.config import dictConfig
from typing import Optional, Tuple

from charli3_dendrite.backend import set_backend
from charli3_dendrite.backend.blockfrost import BlockFrostBackend
from charli3_dendrite.backend.ogmios_kupo import OgmiosKupoBackend
from charli3_offchain_core import ChainQuery, Node
from pycardano import (
    Address,
    AssetName,
    BlockFrostChainContext,
    ExtendedSigningKey,
    HDWallet,
    KupoOgmiosV6ChainContext,
    MultiAsset,
    Network,
    PaymentSigningKey,
    PaymentVerificationKey,
    ScriptHash,
    TransactionId,
    TransactionInput,
)

from backend.api import NodeSyncApi
from backend.api.aggregated_coin_rate import AggregatedCoinRate
from backend.db.crud.feed_crud import feed_crud
from backend.db.database import get_session
from backend.db.models.feed import Feed
from backend.db.models.provider import Provider
from backend.logfiles.logging_config import LEVEL_COLORS, get_log_config
from backend.runner import FeedUpdater
from backend.utils.alerts import AlertManager
from backend.utils.config_utils import RewardCollectionConfig

logger = logging.getLogger(__name__)


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
def setup_ogmios_context(config, network) -> Optional[KupoOgmiosV6ChainContext]:
    """Setup the Ogmios chain context based on the specified configuration."""
    ogmios_config = config.get("ogmios")
    if ogmios_config and "ws_url" in ogmios_config and ogmios_config["ws_url"]:
        ogmios_ws_url = ogmios_config["ws_url"]
        kupo_url = ogmios_config.get("kupo_url")
        _, ws_string = ogmios_ws_url.split("ws://")
        ws_url, port = ws_string.split(":")
        return KupoOgmiosV6ChainContext(
            host=ws_url,
            port=int(port),
            secure=False,
            refetch_chain_tip_interval=None,
            network=network,
            kupo_url=kupo_url,
        )
    return None


# Setup Chain Query
def setup_chain_query(config, network) -> Optional[ChainQuery]:
    """Setup the chain query based on the specified configuration."""
    chain_query_config = config.get("ChainQuery")
    node_config = config.get("Node")
    use_slot_time = chain_query_config.get("use_slot_time", False)
    logger.debug("The variable use_slot_time set to: %s", use_slot_time)
    if chain_query_config:
        setup_charli3dendrite_backend(chain_query_config)
        return ChainQuery(
            blockfrost_context=setup_blockfrost_context(chain_query_config, network),
            kupo_ogmios_context=setup_ogmios_context(chain_query_config, network),
            oracle_address=node_config["oracle_address"],
            use_slot_time=use_slot_time,
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


def setup_charli3dendrite_backend(chain_query_config):
    """Setup the Charli3 Dendrite backend based on the configuration."""
    network_config = chain_query_config.get("network", "").lower()
    external_config = chain_query_config.get("external", {})

    # if the network is Testnet, configure external Ogmios or Blockfrost for Charli3-Dendrite
    if network_config == "testnet":
        blockfrost_config = external_config.get("blockfrost", {})
        blockfrost_id = blockfrost_config.get("project_id")

        external_ogmios_config = external_config.get("ogmios", {})
        external_ws_url = external_ogmios_config.get("ws_url")
        external_kupo_url = external_ogmios_config.get("kupo_url")

        if external_ws_url and external_kupo_url:
            # if external ogmios exists, set up backend with Ogmios Configs
            set_backend(
                OgmiosKupoBackend(
                    external_ws_url,
                    external_kupo_url,
                    Network.MAINNET,
                )
            )
            logger.warning("External Ogmios backend configured for Charli3-Dendrite.")

        elif blockfrost_id:
            set_backend(BlockFrostBackend(blockfrost_id))
            logger.warning("Blockfrost backend configured for Charli3-Dendrite.")

        else:
            logger.error("❌ External Ogmios or Blockfrost configuration is missing.")
            return False

    else:
        ogmios_config = chain_query_config.get("ogmios", {})
        set_backend(
            OgmiosKupoBackend(
                ogmios_config.get("ws_url"),
                ogmios_config.get("kupo_url"),
                Network.MAINNET,
            )
        )
        logger.warning("Ogmios backend configured for Charli3-Dendrite.")

    return True


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


async def setup_aggregated_coin_rate(
    config,
    chain_query: ChainQuery,
    feed_id: str,
    alerts_manager: Optional[AlertManager],
) -> Tuple[AggregatedCoinRate, list[Provider]]:
    """Setup the aggregated coin rate based on the specified configuration."""
    providers = []
    db_providers: list[Provider] = []
    quote_currency = config["Rate"].get("quote_currency")
    quote_symbol = (
        config["Rate"].get("general_quote_symbol") if quote_currency else None
    )

    async with get_session() as db_session:
        rate_class = AggregatedCoinRate(
            quote_currency=quote_currency,
            quote_symbol=quote_symbol,
            chain_query=chain_query,
            feed_id=feed_id,
            alerts_manager=alerts_manager,
        )

        # Add quote data providers
        if rate_class.quote_currency:
            quote_providers, db_quote_providers = await rate_class.add_providers(
                config=config["Rate"]["quote_currency"],
                db_session=db_session,
                pair_type="quote",
            )
            providers.extend(quote_providers)
            db_providers.extend(db_quote_providers)

        # Add base data providers
        base_providers, db_base_providers = await rate_class.add_providers(
            config=config["Rate"]["base_currency"],
            db_session=db_session,
            pair_type="base",
        )
        providers.extend(base_providers)
        db_providers.extend(db_base_providers)

    for provider in providers:
        provider.log_summary()

    return rate_class, db_providers


# Setup Feed Updater
async def setup_feed_updater(
    config, chainquery: ChainQuery, feed: Feed, node: Node
) -> Optional[FeedUpdater]:
    """Setup the feed updater based on the specified configuration."""
    updater_config = config.get("Updater")
    node_sync_config = config.get("NodeSync")
    network = setup_network(config)
    alerts_config = config.get("Alerts", {})
    feed_name = config.get("Rate").get("general_base_symbol", None)
    min_requirement = config.get("Rate").get("min_requirement", True)

    alerts_manager = setup_alerts_manager(
        chainquery, feed_name, alerts_config, network, min_requirement
    )
    reward_collection_config = parse_reward_collection_config(config)

    aggregated_rate, db_providers = await setup_aggregated_coin_rate(
        config, chainquery, feed.id, alerts_manager
    )

    if updater_config:
        node_sync_api = None
        if "api_url" in node_sync_config:
            node_sync_api = NodeSyncApi(node_sync_config.get("api_url"))
            await node_sync_api.report_initialization(feed, node, db_providers)

        return FeedUpdater(
            update_inter=int(updater_config["update_inter"]),
            percent_resolution=int(updater_config["percent_resolution"]),
            reward_collection_config=reward_collection_config,
            node=node,
            rate=aggregated_rate,
            context=chainquery,
            feed_id=feed.id,
            node_sync_api=node_sync_api,
            alerts_manager=alerts_manager,
        )
    return None


def setup_alerts_manager(
    chainquery: ChainQuery,
    feed_name: str,
    alerts_config: dict,
    network: Network,
    min_requirement: bool,
) -> Optional[AlertManager]:
    """Setup the AlertManager based on the provided configuration."""
    notification_configs = alerts_config.get("notifications", [])

    if not notification_configs:
        logger.warning(
            "No alert notifications configured. AlertManager will not be initialized."
        )
        return None

    alert_config = {
        "cooldown": alerts_config.get("cooldown", 1800),
        "thresholds": alerts_config.get("thresholds", {}),
    }

    logger.info(
        "Initializing AlertManager with %d notification configs",
        len(notification_configs),
    )

    return AlertManager(
        feed_name=feed_name,
        chain_query=chainquery,
        alert_config=alert_config,
        notification_configs=notification_configs,
        network=network,
        min_requirement=min_requirement,
    )


def parse_reward_collection_config(config: dict) -> Optional[RewardCollectionConfig]:
    """Parse the reward collection configuration from the specified configuration."""

    reward_config = config.get("RewardCollection")
    if (
        not reward_config
        or "destination_address" not in reward_config
        or "trigger_amount" not in reward_config
    ):
        return None

    return RewardCollectionConfig(
        destination_address=Address.from_primitive(
            reward_config["destination_address"]
        ),
        trigger_amount=int(
            reward_config["trigger_amount"] * 1_000_000
        ),  # Convert ADA to lovelace
    )
