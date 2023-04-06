#!/usr/bin/env python3
"""Abstracts the calls to the chain index API."""
import logging
import asyncio
from blockfrost import ApiError
from pycardano import (
    BlockFrostChainContext,
    OgmiosChainContext,
    Transaction,
    TransactionOutput,
    TransactionBuilder,
)

logger = logging.getLogger("ChainQuery")


class ChainQuery:
    """chainQuery methods"""

    def __init__(
        self,
        blockfrost_context: BlockFrostChainContext = None,
        ogmios_context: OgmiosChainContext = None,
        oracle_address: str = None,
    ):
        if blockfrost_context is None and ogmios_context is None:
            raise ValueError("At least one of the chain contexts must be provided.")

        self.blockfrost_context = blockfrost_context
        self.ogmios_context = ogmios_context
        self.oracle_address = oracle_address
        self.context = blockfrost_context if blockfrost_context else ogmios_context

    async def get_utxos(self, address=None):
        """get utxos from oracle address."""
        if address is None:
            address = self.oracle_address
        if self.blockfrost_context is not None:
            logger.info("Getting utxos from blockfrost")
            return self.blockfrost_context.utxos(str(address))
        elif self.ogmios_context is not None:
            logger.info("Getting utxos from ogmios")
            return self.ogmios_context.utxos(str(address))

    async def wait_for_tx(self, tx_id):
        """
        Waits for a transaction with the given ID to be confirmed.
        Retries the API call every 20 seconds if the transaction is not found.
        Stops retrying after a certain number of attempts.
        """

        async def _wait_for_tx(context, tx_id, check_fn, retries=0, max_retries=10):
            """Wait for a transaction to be confirmed."""
            while retries < max_retries:
                try:
                    response = await check_fn(context, tx_id)
                    if response:
                        logger.info("Transaction submitted with tx_id: %s", str(tx_id))
                        return response

                except ApiError as err:
                    if err.status_code == 404:
                        pass
                    else:
                        raise err

                except Exception as err:
                    raise err

                wait_time = 10 if isinstance(context, OgmiosChainContext) else 20
                logger.info(
                    "Waiting for transaction confirmation: %s. Retrying in %d seconds",
                    str(tx_id),
                    wait_time,
                )
                retries += 1
                await asyncio.sleep(wait_time)

            logger.error(
                "Transaction not found after %d retries. Giving up.", max_retries
            )

        async def check_blockfrost(context, tx_id):
            return context.api.transaction(tx_id)

        async def check_ogmios(context, tx_id):
            response = context._query_utxos_by_tx_id(tx_id, 0)
            return response if response != [] else None

        if self.ogmios_context:
            return await _wait_for_tx(self.ogmios_context, tx_id, check_ogmios)
        elif self.blockfrost_context:
            return await _wait_for_tx(self.blockfrost_context, tx_id, check_blockfrost)

    async def submit_tx_with_print(self, tx: Transaction):
        """submitting the tx."""
        logger.info("Submitting transaction: %s", str(tx.id))
        logger.debug("tx: %s", tx)

        if self.ogmios_context is not None:
            logger.info("Submitting tx with ogmios")
            self.ogmios_context.submit_tx(tx.to_cbor())
        elif self.blockfrost_context is not None:
            logger.info("Submitting tx with blockfrost")
            self.blockfrost_context.submit_tx(tx.to_cbor())

        await self.wait_for_tx(str(tx.id))

    async def find_collateral(self, target_address):
        """method to find collateral utxo."""
        try:
            utxos = await self.get_utxos(address=target_address)
            for utxo in utxos:
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
