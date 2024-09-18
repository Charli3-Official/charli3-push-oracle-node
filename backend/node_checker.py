import logging

from charli3_offchain_core import ChainQuery, Node

from backend.validators import ConfigValidator, HealthCheckValidator
from backend.validators.node_operation_validator import NodeOperationValidator

logger = logging.getLogger(__name__)


class NodeChecker:
    def __init__(self, config):
        self.config_validator = ConfigValidator(config)
        self.health_validator = HealthCheckValidator(config)
        self.node_operation_validator = NodeOperationValidator(config)

    def welcome_message(self):
        """Prints a welcome message with ASCII art."""
        try:
            with open("./backend/charli3.txt", "r") as file:
                ascii_art = file.read()
                print(ascii_art)
        except FileNotFoundError:
            logger.warning("ASCII art file not found.")
        logger.info(
            "------------------------------------------------------------------------------"
        )
        logger.info("Welcome to CHARLI3's Node Network as a Node Operator!")
        logger.info(
            "------------------------------------------------------------------------------"
        )

    async def run_initial_checks(self):
        """Run all node health and config checks."""
        self.welcome_message()

        config_valid = self.config_validator.run_config_validation()
        health_valid = await self.health_validator.run_health_checks()

        if not (config_valid and health_valid):
            logger.error("Terminating application.")
            raise SystemExit(1)
        logger.info("Initial Validations passed.")

    async def run_node_operation_checks(
        self, node: Node, chainquery: ChainQuery
    ) -> bool:
        """Run checks related to node operations."""
        node_valid = await self.node_operation_validator.run_operation_checks(
            node, chainquery
        )
        if not (node_valid):
            logger.error("Terminating application.")
            raise SystemExit(1)
        logger.info("Node Operation Checks Passed.")
