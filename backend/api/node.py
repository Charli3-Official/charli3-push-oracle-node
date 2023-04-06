"""Node contract transactions class"""
import time
import logging
from copy import deepcopy
from typing import List, Union
import cbor2
from pycardano import (
    Network,
    Address,
    PaymentVerificationKey,
    PaymentSigningKey,
    ExtendedSigningKey,
    AssetName,
    TransactionOutput,
    TransactionBuilder,
    Redeemer,
    RedeemerTag,
    Asset,
    MultiAsset,
    UTxO,
    ScriptHash,
    Value,
    TransactionInput,
    PlutusV2Script,
    plutus_script_hash,
)
from backend.core.datums import (
    NodeDatum,
    NodeInfo,
    PriceFeed,
    DataFeed,
    AggDatum,
    OracleDatum,
    PriceData,
)
from backend.core.redeemers import (
    NodeUpdate,
    Aggregate,
    UpdateAndAggregate,
    NodeCollect,
)
from backend.core.aggregate_conditions import aggregation_conditions
from .chainquery import ChainQuery, ApiError
from .oraclechecks import check_utxo_asset_balance, get_oracle_utxos_with_datums

logger = logging.getLogger("Node")


class Node:
    """node transaction implementation"""

    def __init__(
        self,
        network: Network,
        chain_query: ChainQuery,
        signing_key: Union[PaymentSigningKey, ExtendedSigningKey],
        verification_key: PaymentVerificationKey,
        node_nft: MultiAsset,
        aggstate_nft: MultiAsset,
        oracle_nft: MultiAsset,
        oracle_addr: Address,
        c3_token_hash: ScriptHash,
        c3_token_name: AssetName,
        reference_script_input: Union[None, TransactionInput],
    ) -> None:
        self.network = network
        self.chain_query = chain_query
        self.context = self.chain_query.context
        self.signing_key = signing_key
        self.verification_key = verification_key
        self.pub_key_hash = self.verification_key.hash()
        self.address = Address(payment_part=self.pub_key_hash, network=self.network)
        self.node_nft = node_nft
        self.aggstate_nft = aggstate_nft
        self.oracle_nft = oracle_nft
        self.node_info = NodeInfo(bytes.fromhex(str(self.pub_key_hash)))
        self.oracle_addr = oracle_addr
        self.c3_token_hash = c3_token_hash
        self.c3_token_name = c3_token_name
        self.oracle_script_hash = self.oracle_addr.payment_part
        self.reference_script_input = reference_script_input
        self.oracle_script_hash = self.oracle_addr.payment_part

    async def update(self, rate: int):
        """build's partial node update tx."""
        logger.info("node update called: %d", rate)
        oracle_utxos = await self.chain_query.get_utxos(self.oracle_addr)
        node_own_utxo = self.get_node_own_utxo(oracle_utxos)
        time_ms = round(time.time_ns() * 1e-6)
        new_node_feed = PriceFeed(DataFeed(rate, time_ms))

        node_own_utxo.output.datum.node_state.node_feed = new_node_feed

        node_update_redeemer = Redeemer(RedeemerTag.SPEND, NodeUpdate())

        builder = TransactionBuilder(self.context)

        script_utxo = (
            self.get_reference_script_utxo(oracle_utxos)
            if self.reference_script_input
            else None
        )

        builder.add_script_input(
            node_own_utxo, script=script_utxo, redeemer=node_update_redeemer
        ).add_output(node_own_utxo.output)

        await self.submit_tx_builder(builder)

    async def aggregate(self, rate: int = None, update_node_output: bool = False):
        """build's partial node aggregate tx."""
        oracle_utxos = await self.chain_query.get_utxos(self.oracle_addr)
        curr_time_ms = round(time.time_ns() * 1e-6)
        oraclefeed_utxo, aggstate_utxo, nodes_utxos = get_oracle_utxos_with_datums(
            oracle_utxos, self.aggstate_nft, self.oracle_nft, self.node_nft
        )
        aggstate_datum: AggDatum = aggstate_utxo.output.datum
        oraclefeed_datum: OracleDatum = oraclefeed_utxo.output.datum
        total_nodes = len(aggstate_datum.aggstate.ag_settings.os_node_list)
        single_node_fee = (
            aggstate_datum.aggstate.ag_settings.os_node_fee_price.get_node_fee
        )
        min_c3_required = single_node_fee * total_nodes

        # Handling update_aggregate logic here.
        if update_node_output:
            new_node_feed = PriceFeed(DataFeed(rate, curr_time_ms))
            nodes_utxos = self.update_own_node_utxo(nodes_utxos, new_node_feed)

        # Calculations and Conditions check for aggregation.
        if check_utxo_asset_balance(
            aggstate_utxo, self.c3_token_hash, self.c3_token_name, min_c3_required
        ):
            valid_nodes, agg_value = aggregation_conditions(
                aggstate_datum.aggstate.ag_settings,
                oraclefeed_datum,
                bytes(self.pub_key_hash),
                curr_time_ms,
                nodes_utxos,
            )

            if len(valid_nodes) > 0 and set(valid_nodes).issubset(set(nodes_utxos)):
                c3_fees = len(valid_nodes) * single_node_fee
                oracle_feed_expiry = (
                    curr_time_ms + aggstate_datum.aggstate.ag_settings.os_aggregate_time
                )

                if update_node_output:
                    aggregate_redeemer = Redeemer(
                        RedeemerTag.SPEND,
                        UpdateAndAggregate(pub_key_hash=bytes(self.pub_key_hash)),
                    )
                else:
                    logger.info("aggregate called with agg_value: %d", agg_value)
                    aggregate_redeemer = Redeemer(RedeemerTag.SPEND, Aggregate())

                script_utxo = (
                    self.get_reference_script_utxo(oracle_utxos)
                    if self.reference_script_input
                    else None
                )

                builder = TransactionBuilder(self.context)

                aggstate_tx_output = deepcopy(aggstate_utxo.output)
                aggstate_tx_output.amount.multi_asset[self.c3_token_hash][
                    self.c3_token_name
                ] -= c3_fees

                oraclefeed_tx_output = deepcopy(oraclefeed_utxo.output)
                oraclefeed_tx_output.datum = OracleDatum(
                    PriceData.set_price_map(agg_value, curr_time_ms, oracle_feed_expiry)
                )

                (
                    builder.add_script_input(
                        aggstate_utxo,
                        script=script_utxo,
                        redeemer=deepcopy(aggregate_redeemer),
                    )
                    .add_script_input(
                        oraclefeed_utxo,
                        script=script_utxo,
                        redeemer=deepcopy(aggregate_redeemer),
                    )
                    .add_output(aggstate_tx_output)
                    .add_output(oraclefeed_tx_output)
                )

                for utxo in valid_nodes:
                    builder.add_script_input(
                        utxo, script=script_utxo, redeemer=deepcopy(aggregate_redeemer)
                    )
                    tx_output = deepcopy(utxo.output)
                    if (
                        self.c3_token_hash in tx_output.amount.multi_asset
                        and self.c3_token_name
                        in tx_output.amount.multi_asset[self.c3_token_hash]
                    ):
                        tx_output.amount.multi_asset[self.c3_token_hash][
                            self.c3_token_name
                        ] += single_node_fee
                    else:
                        # Handle the case where the key does not exist
                        # For example, set the value to a default value
                        c3_asset = MultiAsset(
                            {
                                self.c3_token_hash: Asset(
                                    {self.c3_token_name: single_node_fee}
                                )
                            }
                        )
                        tx_output.amount.multi_asset += c3_asset

                    builder.add_output(tx_output)

                await self.submit_tx_builder(builder)
            else:
                logger.error(
                    "The required minimum number of nodes for aggregation has not been met. \
                     aggregation conditions failed."
                )

        else:
            logger.error("Not enough C3s to perform aggregation")

    async def update_aggregate(self, rate: int):
        """build's partial node update_aggregate tx."""
        logger.info("update-aggregate called: %d ", rate)
        await self.aggregate(rate=rate, update_node_output=True)

    async def collect(self):
        """build's partial node collect tx."""
        oracle_utxos = await self.chain_query.get_utxos(self.oracle_addr)
        node_own_utxo = self.get_node_own_utxo(oracle_utxos)

        # preparing multiasset.
        c3_amount = node_own_utxo.output.amount.multi_asset[self.c3_token_hash][
            self.c3_token_name
        ]

        c3_asset = MultiAsset(
            {self.c3_token_hash: Asset({self.c3_token_name: c3_amount})}
        )

        tx_output = deepcopy(node_own_utxo.output)
        tx_output.amount.multi_asset -= c3_asset

        node_collect_redeemer = Redeemer(RedeemerTag.SPEND, NodeCollect())

        builder = TransactionBuilder(self.context)

        (
            builder.add_script_input(node_own_utxo, redeemer=node_collect_redeemer)
            .add_output(tx_output)
            .add_output(TransactionOutput(self.address, Value(2000000, c3_asset)))
        )

        await self.submit_tx_builder(builder)

    async def submit_tx_builder(self, builder: TransactionBuilder):
        """adds collateral and signers to tx , sign and submit tx."""
        # abstracting common inputs here.
        builder.add_input_address(self.address)
        builder.add_output(TransactionOutput(self.address, 5000000))

        try:
            non_nft_utxo = await self.chain_query.find_collateral(self.address)

            if non_nft_utxo is None:
                await self.chain_query.create_collateral(self.address, self.signing_key)
                non_nft_utxo = await self.chain_query.find_collateral(self.address)

            if non_nft_utxo is not None:
                builder.collaterals.append(non_nft_utxo)
                builder.required_signers = [self.pub_key_hash]

                signed_tx = builder.build_and_sign(
                    [self.signing_key], change_address=self.address
                )
                await self.chain_query.submit_tx_with_print(signed_tx)
            else:
                logger.error("collateral utxo is None.")

        except ApiError as err:
            if err.status_code == 404:
                logger.error("No utxos found at the node address, fund the wallet.")

    def get_node_own_utxo(self, oracle_utxos: List[UTxO]) -> UTxO:
        """returns node's own utxo from list of oracle UTxOs"""
        nodes_utxos = self.filter_utxos_by_asset(oracle_utxos, self.node_nft)
        return self.filter_node_utxos_by_node_info(nodes_utxos)

    def filter_utxos_by_asset(self, utxos: List[UTxO], asset: MultiAsset) -> List[UTxO]:
        """filter list of UTxOs by given asset"""
        return list(filter(lambda x: x.output.amount.multi_asset >= asset, utxos))

    def filter_node_utxos_by_node_info(self, nodes_utxo: List[UTxO]) -> UTxO:
        """filter list of UTxOs by given node_info"""
        if len(nodes_utxo) > 0:
            for utxo in nodes_utxo:
                if utxo.output.datum:
                    if utxo.output.datum.cbor:
                        utxo.output.datum = NodeDatum.from_cbor(utxo.output.datum.cbor)

                    if utxo.output.datum.node_state.node_operator == self.node_info:
                        return utxo
        return None

    def update_own_node_utxo(
        self, nodes_utxo: List[UTxO], updated_node_feed: PriceFeed
    ) -> List[UTxO]:
        """update own node utxo and return node utxos"""
        if len(nodes_utxo) > 0:
            for utxo in nodes_utxo:
                if utxo.output.datum.node_state.node_operator == self.node_info:
                    utxo.output.datum.node_state.node_feed = updated_node_feed

        return nodes_utxo

    def get_reference_script_utxo(self, utxos: List[UTxO]) -> UTxO:
        """patch if no reference script found."""
        if len(utxos) > 0:
            for utxo in utxos:
                if utxo.input == self.reference_script_input:
                    script = self.get_plutus_script(self.oracle_script_hash)
                    utxo.output.script = script
                    return utxo

    def get_plutus_script(self, scripthash: ScriptHash) -> PlutusV2Script:
        """function to get plutus script and verify it's script hash"""
        plutus_script = self.context._get_script(str(scripthash))
        if plutus_script_hash(plutus_script) != scripthash:
            plutus_script = PlutusV2Script(cbor2.dumps(plutus_script))
        if plutus_script_hash(plutus_script) == scripthash:
            return plutus_script
        else:
            logger.error("script hash mismatch")
