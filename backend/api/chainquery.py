#!/usr/bin/env python3
"""Abstracts the calls to the chain index API."""
import logging
import asyncio
from blockfrost import ApiError
from pycardano import (
    BlockFrostChainContext,
    Network,
    Transaction,
    TransactionOutput,
    TransactionBuilder,
)

logger = logging.getLogger("ChainQuery")


class ChainQuery(BlockFrostChainContext):
    """chainQuery methods"""

    def __init__(
        self,
        project_id: str,
        network: Network = Network.TESTNET,
        base_url: str = None,
        oracle_address: str = None,
    ):
        super().__init__(project_id=project_id, network=network, base_url=base_url)
        self.oracle_address = oracle_address

    async def get_utxos(self):
        """get utxos from oracle address."""
        return self.utxos(str(self.oracle_address))

    async def wait_for_tx(self, tx_id):
        """
        Waits for a transaction with the given ID to be confirmed.
        Retries the API call every 20 seconds if the transaction is not found.
        Stops retrying after a certain number of attempts.
        """
        retries = 0
        max_retries = 10

        while retries < max_retries:
            try:
                # Make the API call to check the status of the transaction
                response = self.api.transaction(tx_id)
                logger.info("Transaction submitted with tx_id: %s", str(tx_id))
                return response
            except ApiError as err:
                if err.status_code == 404:
                    logger.info(
                        "Waiting for transaction confirmation: %s. Retrying in 20 seconds",
                        str(tx_id),
                    )
                    retries += 1
                    await asyncio.sleep(20)
                else:
                    raise err
        logger.error("Transaction not found after %d retries. Giving up.", max_retries)

    async def submit_tx_with_print(self, tx: Transaction):
        """submitting the tx."""
        logger.info("Submitting transaction: %s", str(tx.id))
        logger.debug("tx: %s", tx)
        self.submit_tx(tx.to_cbor())
        await self.wait_for_tx(str(tx.id))

    async def find_collateral(self, target_address):
        """method to find collateral utxo."""
        try:
            for utxo in self.utxos(str(target_address)):
                # A collateral should contain no multi asset
                if not utxo.output.amount.multi_asset:
                    if utxo.output.amount < 10000000:
                        if utxo.output.amount.coin >= 5000000:
                            return utxo
        except ApiError as err:
            if err.status_code == 404:
                logger.info("No utxos found")
                raise err
            else:
                logger.warning(
                    "Requirements for collateral couldn't be satisfied. need an utxo of >= 5000000\
                    and < 10000000, %s",
                    err,
                )
        return None

    async def create_collateral(self, target_address, skey):
        """create collateral utxo"""
        logger.info("creating collateral UTxO.")
        collateral_builder = TransactionBuilder(self)

        collateral_builder.add_input_address(target_address)
        collateral_builder.add_output(TransactionOutput(target_address, 5000000))

        await self.submit_tx_with_print(
            collateral_builder.build_and_sign([skey], target_address)
        )
