"""Main file for the backend"""
import logging
import asyncio
import argparse
from logging.config import dictConfig
import yaml
from pycardano import (
    Network,
    Address,
    PaymentVerificationKey,
    PaymentSigningKey,
    ExtendedSigningKey,
    ScriptHash,
    AssetName,
    MultiAsset,
    HDWallet,
    TransactionInput,
    TransactionId,
    BlockFrostChainContext,
    OgmiosChainContext,
)
from charli3_offchain_core import Node, ChainQuery
from backend.api import AggregatedCoinRate
from backend.runner import FeedUpdater
from backend.logfiles.logging_config import get_log_config, LEVEL_COLORS


# Loads configuration file
parser = argparse.ArgumentParser(
    prog="Charli3 Backends for Node Operator",
    description="Charli3 Backends for Node Opetor.",
)

parser.add_argument(
    "-c",
    "--configfile",
    help="Specify a file to override default configuration",
    default="config.yml",
)

arguments = parser.parse_args()

with open(arguments.configfile, "r", encoding="UTF-8") as ymlfile:
    configyaml = yaml.load(ymlfile, Loader=yaml.FullLoader)

ini_updater = configyaml["Updater"]
ini_node = configyaml["Node"]
chain_query_config = configyaml["ChainQuery"]

# Generates instances of classes from configuration file

if ini_node:
    if chain_query_config["network"] == "TESTNET":
        network = Network.TESTNET
    elif chain_query_config["network"] == "MAINNET":
        network = Network.MAINNET

    blockfrost_config = chain_query_config.get("blockfrost")
    ogmios_config = chain_query_config.get("ogmios")

    if blockfrost_config:
        blockfrost_base_url = blockfrost_config["base_url"]
        blockfrost_project_id = blockfrost_config["project_id"]

        blockfrost_context = BlockFrostChainContext(
            blockfrost_project_id,
            network,
            base_url=blockfrost_base_url,
        )

    if ogmios_config:
        ogmios_ws_url = ogmios_config["ws_url"]
        kupo_url = ogmios_config.get("kupo_url")

        ogmios_context = OgmiosChainContext(
            network=network,
            ws_url=ogmios_ws_url,
            kupo_url=kupo_url,
        )

    chain_query = ChainQuery(
        blockfrost_context=blockfrost_context if blockfrost_config else None,
        ogmios_context=ogmios_context if ogmios_config else None,
        oracle_address=ini_node["oracle_addr"],
    )

    oracle_nft_hash = ScriptHash.from_primitive(ini_node["oracle_curr"])

    node_nft = MultiAsset.from_primitive(
        {oracle_nft_hash.payload: {bytes(ini_node["node_nft"], "utf-8"): 1}}
    )
    oracle_nft = MultiAsset.from_primitive(
        {oracle_nft_hash.payload: {bytes(ini_node["oracle_nft"], "utf-8"): 1}}
    )
    aggstate_nft = MultiAsset.from_primitive(
        {oracle_nft_hash.payload: {bytes(ini_node["aggstate_nft"], "utf-8"): 1}}
    )
    reward_nft = MultiAsset.from_primitive(
        {oracle_nft_hash.payload: {bytes(ini_node["reward_nft"], "utf-8"): 1}}
    )

    if "mnemonic" in ini_node and ini_node["mnemonic"]:
        hdwallet = HDWallet.from_mnemonic(ini_node["mnemonic"])
        hdwallet_spend = hdwallet.derive_from_path("m/1852'/1815'/0'/0/0")
        spend_public_key = hdwallet_spend.public_key
        node_vk = PaymentVerificationKey.from_primitive(spend_public_key)
        node_sk = ExtendedSigningKey.from_hdwallet(hdwallet_spend)

    elif ini_node["signing_key"] and ini_node["verification_key"]:
        node_sk = PaymentSigningKey.load(ini_node["signing_key"])
        node_vk = PaymentVerificationKey.load(ini_node["verification_key"])

    if "reference_script_input" in ini_node and ini_node["reference_script_input"]:
        tx_id_hex, index = ini_node["reference_script_input"].split("#")
        tx_id = TransactionId(bytes.fromhex(tx_id_hex))
        index = int(index)
        reference_script_input = TransactionInput(tx_id, index)
    else:
        reference_script_input = None

    if "c3_oracle_rate_address" in ini_node and ini_node["c3_oracle_rate_address"]:
        c3_oracle_rate_address = Address.from_primitive(
            ini_node["c3_oracle_rate_address"]
        )
    else:
        c3_oracle_rate_address = None

    if "c3_oracle_nft_hash" in ini_node and ini_node["c3_oracle_nft_hash"]:
        c3_oracle_nft_hash = ScriptHash.from_primitive(ini_node["c3_oracle_nft_hash"])
    else:
        c3_oracle_nft_hash = None

    if "c3_oracle_nft_name" in ini_node and ini_node["c3_oracle_nft_name"]:
        c3_oracle_nft_name = ini_node["c3_oracle_nft_name"]
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
        Address.from_primitive(ini_node["oracle_addr"]),
        ScriptHash.from_primitive(ini_node["c3_token_hash"]),
        AssetName(bytes(ini_node["c3_token_name"], "utf-8")),
        reference_script_input,
        oracle_rate_addr=c3_oracle_rate_address,
        oracle_rate_nft=c3_oracle_nft,
    )

if "quote_currency" in configyaml["Rate"] and configyaml["Rate"]["quote_currency"]:
    rateclass = AggregatedCoinRate(quote_currency=True)

    for provider in configyaml["Rate"]["quote_currency"]:
        feed_type = configyaml["Rate"]["quote_currency"][provider]["type"]
        del configyaml["Rate"]["quote_currency"][provider]["type"]

        rateclass.add_quote_data_provider(
            feed_type, provider, configyaml["Rate"]["quote_currency"][provider]
        )

else:
    rateclass = AggregatedCoinRate()

for provider in configyaml["Rate"]["base_currency"]:
    feed_type = configyaml["Rate"]["base_currency"][provider]["type"]
    del configyaml["Rate"]["base_currency"][provider]["type"]

    rateclass.add_base_data_provider(
        feed_type, provider, configyaml["Rate"]["base_currency"][provider]
    )

updater = FeedUpdater(
    int(ini_updater["update_inter"]),
    int(ini_updater["percent_resolution"]),
    node,
    rateclass,
    chain_query,
)

logconfig = get_log_config(ini_updater)

if "awslogger" in configyaml:
    logconfig["handlers"]["kinesis"] = {
        "class": "backend.logfiles.KinesisFirehose.DeliveryStreamHandler",
        "formatter": "json",
        "configyml": configyaml["awslogger"],
    }
    logconfig["loggers"][""]["handlers"].append("kinesis")


dictConfig(logconfig)

old_factory = logging.getLogRecordFactory()


def _record_factory(*args, **kwargs):
    record = old_factory(*args, **kwargs)
    record.node = node.pub_key_hash
    record.feed = ini_node["oracle_curr"]
    record.level_color = LEVEL_COLORS[record.levelno // 10]
    record.end_color = "\033[0m"
    return record


logging.setLogRecordFactory(_record_factory)

asyncio.run(updater.run())
