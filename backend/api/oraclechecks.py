"""Implementing Oracle checks and filters"""
import logging
from typing import List, Tuple
from pycardano import (
    UTxO,
    MultiAsset,
    ScriptHash,
    AssetName,
)
from backend.core.datums import NodeDatum, OracleDatum, AggDatum, RewardDatum

logger = logging.getLogger("oracle-checks")


def filter_node_datums_by_node_operator(
    node_datums: List[NodeDatum], node_operator: bytes
):
    """
    filter node datums by node info

    Args:
        node_datums: A list of NodeDatum objects.
        node_operator: A NodeInfo object.

    Returns:
        A NodeDatum object.

    """
    if len(node_datums) > 0:
        for node_datum in node_datums:
            if node_datum.node_state.ns_operator == node_operator:
                return node_datum
    return None


def check_utxo_asset_balance(
    input_utxo: UTxO,
    asset_policy_id: ScriptHash,
    token_name: AssetName,
    min_amount: int,
) -> bool:
    """Check if input UTxO has minimum asset balance.

    Args:
        input_utxo: The UTxO object to check.
        asset_policy_id: The asset policy ID to use.
        token_name: The token name to use.
        min_amount: The minimum amount required.

    Returns:
        True if the input UTxO has at least the minimum required balance, False otherwise.
    """
    if input_utxo.output.amount.multi_asset is None:
        return False

    if input_utxo.output.amount.multi_asset[asset_policy_id] is None:
        return False

    if input_utxo.output.amount.multi_asset[asset_policy_id][token_name] is None:
        return False

    # Check if input UTxO has at least the minimum required balance
    return (
        input_utxo.output.amount.multi_asset[asset_policy_id][token_name] >= min_amount
    )


def convert_cbor_to_node_datums(node_utxos: List[UTxO]) -> List[UTxO]:
    """
    Convert CBOR encoded NodeDatum objects to their corresponding Python objects.

    Parameters:
    - node_utxos (List[UTxO]): A list of UTxO objects that contain NodeDatum objects in CBOR
      encoding.

    Returns:
    - A list of UTxO objects that contain NodeDatum objects in their original Python format.
    """
    result: List[UTxO] = []

    if len(node_utxos) > 0:
        for utxo in node_utxos:
            if utxo.output.datum:
                node_datum: NodeDatum = NodeDatum.from_cbor(utxo.output.datum.cbor)
                utxo.output.datum = node_datum
                result.append(utxo)
    return result


def get_oracle_utxos_with_datums(
    oracle_utxos: List[UTxO],
    aggstate_nft: MultiAsset,
    oracle_nft: MultiAsset,
    reward_nft: MultiAsset,
    node_nft: MultiAsset,
) -> Tuple[UTxO, UTxO, UTxO, List[UTxO]]:
    """
    Given a list of UTxOs, filters them by asset and converts the data to the appropriate datum
    object.

    Parameters:
        - oracle_utxos (List[UTxO]): The list of UTxOs to filter and convert.
        - aggstate_nft (MultiAsset): The asset used to filter the UTxOs for the AggDatum object.
        - oracle_nft (MultiAsset): The asset used to filter the UTxOs for the OracleDatum object.
        - reward_nft (MultiAsset): The asset used to filter the UTxOs for the RewardDatum object.
        - node_nft (MultiAsset): The asset used to filter the UTxOs for the NodeDatum objects.

    Returns:
        Tuple[UTxO, UTxO, UTxO, List[UTxO]] : A tuple containing the filtered and
        converted UTxOs for the AggDatum, OracleDatum, RewardDatum, and
        NodeDatum  objects.
    """
    aggstate_utxo = next(
        (
            utxo
            for utxo in oracle_utxos
            if utxo.output.amount.multi_asset >= aggstate_nft
        ),
        None,
    )
    oraclefeed_utxo = next(
        (utxo for utxo in oracle_utxos if utxo.output.amount.multi_asset >= oracle_nft),
        None,
    )
    reward_utxo = next(
        (utxo for utxo in oracle_utxos if utxo.output.amount.multi_asset >= reward_nft),
        None,
    )
    nodes_utxos = [
        utxo for utxo in oracle_utxos if utxo.output.amount.multi_asset >= node_nft
    ]
    node_utxos_with_datum = convert_cbor_to_node_datums(nodes_utxos)

    try:
        if aggstate_utxo.output.datum:
            aggstate_utxo.output.datum = AggDatum.from_cbor(
                aggstate_utxo.output.datum.cbor
            )
    except Exception:
        logger.error("Invalid CBOR data for AggDatum")

    try:
        if oraclefeed_utxo.output.datum:
            oraclefeed_utxo.output.datum = OracleDatum.from_cbor(
                oraclefeed_utxo.output.datum.cbor
            )
    except Exception:
        logger.error("Invalid CBOR data for OracleDatum")

    try:
        if reward_utxo.output.datum:
            reward_utxo.output.datum = RewardDatum.from_cbor(
                reward_utxo.output.datum.cbor
            )
    except Exception:
        print("Invalid CBOR data for RewardDatum")

    return (
        oraclefeed_utxo,
        aggstate_utxo,
        reward_utxo,
        node_utxos_with_datum,
    )


def get_oracle_datums_only(
    oracle_utxos: List[UTxO],
    aggstate_nft: MultiAsset,
    oracle_nft: MultiAsset,
    reward_nft: MultiAsset,
    node_nft: MultiAsset,
) -> Tuple[OracleDatum, AggDatum, RewardDatum, List[NodeDatum]]:
    """
    This function takes a list of oracle UTxOs, an aggstate NFT, an oracle NFT,
    a node NFT, and a reward NFT as inputs, and returns a tuple containing the
    oracle datum, the aggstate datum, the reward datum, and a list of node datums.
    Parameters:
    - oracle_utxos (List[UTxO]): A list of oracle UTxOs.
    - aggstate_nft (MultiAsset): The aggstate NFT.
    - oracle_nft (MultiAsset): The oracle NFT.
    - reward_nft (MultiAsset): The reward NFT.
    - node_nft (MultiAsset): The node NFT.

    Returns:
    - Tuple[OracleDatum, AggDatum, RewardDatum, List[NodeDatum]]: A tuple containing
    the oracle datum, the aggstate datum, the reward datum and a list of node datums.
    """

    (
        oraclefeed_utxo,
        aggstate_utxo,
        reward_utxo,
        node_utxos_with_datum,
    ) = get_oracle_utxos_with_datums(
        oracle_utxos, aggstate_nft, oracle_nft, reward_nft, node_nft
    )

    oracle_datum = oraclefeed_utxo.output.datum
    aggstate_datum = aggstate_utxo.output.datum
    reward_datum = reward_utxo.output.datum

    node_datums = [node.output.datum for node in node_utxos_with_datum]

    return (oracle_datum, aggstate_datum, reward_datum, node_datums)
