"""Module for validating node operator eligibility to start operations."""

import logging
from typing import Optional

from charli3_offchain_core import ChainQuery, Node
from charli3_offchain_core.aggregate_conditions import check_aggregator_permission
from charli3_offchain_core.oracle_checks import get_oracle_datums_only

logger = logging.getLogger(__name__)


class NodeOperationValidator:
    """Validates if a node is eligible to start or continue operations."""

    def __init__(self, config):
        """Initialize the validator with configuration data."""
        self.config = config
        self.node: Optional[Node] = None
        self.chainquery: Optional[ChainQuery] = None

    async def check_node_listing(self) -> bool:
        """Check if the node is listed in oracle settings."""
        try:
            # Fetch UTXOs from chainquery
            oracle_utxos = await self.chainquery.get_utxos()

            # Extract necessary datums
            _, agg_datum, _, _ = get_oracle_datums_only(
                oracle_utxos,
                self.node.aggstate_nft,
                self.node.oracle_nft,
                self.node.reward_nft,
                self.node.node_nft,
            )

            # Check if the node has permission in oracle settings
            permission = check_aggregator_permission(
                agg_datum.aggstate.ag_settings, self.node.node_operator
            )

            if not permission:
                logger.error("❌ Node is not listed in oracle settings.")
                logger.info("-------------------MESSAGE----------------")
                logger.info(
                    "Contact Oracle Owner to get your Node Public Key Registered."
                )
                logger.info("Node Public Key: %s", self.node.pub_key_hash)
                logger.info("------------------------------------------")
                return False

            logger.info("✅ Node is listed in oracle settings.")
            return True

        except Exception as exc:
            logger.error("❌ Error checking node listing: %s", exc)
            return False

    def check_initial_balance(self):
        """Placeholder for checking the initial balance of the node."""
        pass

    async def run_operation_checks(self, node: Node, chainquery: ChainQuery) -> bool:
        """Run all the operation checks for a node."""
        self.chainquery = chainquery
        self.node = node
        logger.info(
            "-------------------- Running Operation Checks -----------------------"
        )
        node_valid = await self.check_node_listing()
        if not node_valid:
            logger.info(
                "-------------------- Operation Checks Failed -----------------------"
            )
            return False

        logger.info(
            "-------------------- Operation Checks Passed -----------------------"
        )
        return True
