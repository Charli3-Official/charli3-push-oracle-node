"""Configuration Validator Module."""

import logging

logger = logging.getLogger(__name__)


class ConfigValidator:
    """Configuration Validator Class."""

    REQUIRED_NODE_KEYS = [
        "mnemonic",
        "oracle_curr",
        "oracle_address",
        "c3_token_hash",
        "c3_token_name",
    ]

    def __init__(self, config: dict):
        """
        Initialize the ConfigValidator with the provided configuration.
        Args:
            config (dict): The configuration dictionary to validate.
        """
        self.config = config

    def validate_node_keys(self) -> bool:
        """Ensure all required keys are present in the Node section."""
        missing_keys = [
            key
            for key in self.REQUIRED_NODE_KEYS
            if key not in self.config.get("Node", {})
        ]

        if missing_keys:
            logger.error(
                "❌ Missing required keys in Node section: %s", ", ".join(missing_keys)
            )
            return False

        logger.info("✅ Required Node Configurations are present.")
        return True

    def validate_chain_query_keys(self) -> bool:
        """Ensure all required keys are present in the ChainQuery section."""
        chain_query_section = self.config.get("ChainQuery", {})

        # Check for the 'network' key
        if "network" not in chain_query_section:
            logger.error("❌ 'network' key is missing in ChainQuery section.")
            return False

        network_config = chain_query_section["network"].lower()
        ogmios_section = chain_query_section.get("ogmios", {})
        blockfrost_section = chain_query_section.get("blockfrost", {})

        # Check that Blockfrost and Ogmios are not both configured
        if not self._check_conflicting_configs(ogmios_section, blockfrost_section):
            return False

        if ogmios_section and not self._validate_ogmios_config(
            ogmios_section, "Internal"
        ):
            return False
        if blockfrost_section and not self._validate_blockfrost_config(
            blockfrost_section, False
        ):
            return False

        # For testnet, validate external configurations
        if network_config == "testnet":
            external_section = chain_query_section.get("external", {})
            external_ogmios_section = external_section.get("ogmios", {})
            external_blockfrost_section = external_section.get("blockfrost", {})

            if not self._check_conflicting_configs(
                external_ogmios_section, external_blockfrost_section
            ):
                return False

            if external_ogmios_section and not self._validate_ogmios_config(
                external_ogmios_section, "External"
            ):
                return False
            if external_blockfrost_section and not self._validate_blockfrost_config(
                external_blockfrost_section, True
            ):
                return False

        return True

    def _check_conflicting_configs(
        self, ogmios_section: dict, blockfrost_section: dict
    ) -> bool:
        """Check if both 'ogmios' and 'blockfrost' sections are present, which is a conflict."""
        if ogmios_section and blockfrost_section:
            logger.error(
                "❌ Both 'ogmios' and 'blockfrost' sections are present. Only one should be configured."
            )
            return False
        return True

    def _validate_ogmios_config(self, ogmios_section: dict, config_name: str) -> bool:
        """Validate that 'ws_url' and 'kupo_url' are present in the 'ogmios' section."""
        if "ws_url" not in ogmios_section or "kupo_url" not in ogmios_section:
            logger.error(
                "❌ 'ws_url' and/or 'kupo_url' are missing in the %s Ogmios section.",
                config_name,
            )
            return False
        logger.info("✅ %s Ogmios Configurations are present.", config_name)
        return True

    def _validate_blockfrost_config(
        self, blockfrost_section: dict, is_external: bool
    ) -> bool:
        """Validate that 'project_id' is present in the 'blockfrost' section."""
        project_id = blockfrost_section.get("project_id")
        if not project_id:
            logger.error("❌ 'project_id' is missing in the Blockfrost section.")
            return False

        # For external blockfrost, ensure project_id is for mainnet
        if is_external and ("preprod" in project_id or "preview" in project_id):
            logger.error(
                "❌ External Blockfrost project_id is invalid or should be for Mainnet network."
            )
            return False

        logger.info("✅ Blockfrost Configurations are present.")
        return True

    def validate_rate_keys(self) -> bool:
        """Ensure the Rate section is valid, including general symbols and data sources."""
        rate_section = self.config.get("Rate", {})
        if not rate_section:
            logger.error("❌ Rate is missing in the Configuration.")
            return False

        if "general_base_symbol" not in rate_section:
            logger.error("❌ Missing 'general_base_symbol' in Rate section.")
            return False

        if "min_requirement" in rate_section:
            if not isinstance(rate_section["min_requirement"], bool):
                logger.error("❌ 'min_requirement' in Rate section must be a boolean.")
                return False
        else:
            logger.warning(
                "'min_requirement' not specified in Rate section. Defaulting to True."
            )

        if not self.validate_base_currency() or not self.validate_quote_currency():
            return False

        logger.info("✅ Required Rate Configurations are present.")
        return True

    def validate_base_currency(self) -> bool:
        """Ensure the base currency section is properly configured with at least 3 data sources."""
        base_currency_section = self.config.get("Rate", {}).get("base_currency", {})
        min_requirement = self.config.get("Rate", {}).get("min_requirement", True)
        if not base_currency_section:
            logger.error("❌ Base currency section is missing.")
            return False

        total_sources = 0

        # Count DEX sources
        for dex in base_currency_section.get("dexes", []):
            sources = dex.get("sources", [])
            if not sources:
                total_sources += 7  # If sources is empty, assume it counts as 7.
            else:
                total_sources += len(sources)

        # Count API sources
        for api_source in base_currency_section.get("api_sources", []):
            sources = api_source.get("sources", [])
            total_sources += len(sources)  # 0 is 0 for api_sources.

        if min_requirement and total_sources < 3:
            logger.error(
                "❌ Insufficient base data sources. Found %d, need at least 3.",
                total_sources,
            )
            return False

        logger.info(
            "✅ Base Data Sources requirement met with: %d sources.", total_sources
        )
        return True

    def validate_quote_currency(self) -> bool:
        """Ensure the quote currency section is valid when required by base currency."""
        base_currency_section = self.config.get("Rate", {}).get("base_currency", {})
        quote_currency_section = self.config.get("Rate", {}).get("quote_currency", {})

        quote_required = False

        # Check if any of the dexes or api_sources in base_currency have quote_required = true
        for dex in base_currency_section.get("dexes", []):
            if dex.get("quote_required", False):
                quote_required = True

        for api_source in base_currency_section.get("api_sources", []):
            if api_source.get("quote_required", False):
                quote_required = True

        # If quote_required is true, quote_currency must be present with at least 1 source
        if quote_required:
            if not quote_currency_section:
                logger.error(
                    "❌ Quote currency section is missing but required by base currency."
                )
                return False
            if len(quote_currency_section.get("api_sources", [])) < 1:
                logger.error("At least one quote currency API source is required.")
                return False

        return True

    def run_config_validation(self) -> bool:
        """
        Run all configuration validation checks.
        Returns:
            bool: True if all validations pass, False otherwise.
        """
        logger.info(
            "-------------------- Running Conguration Checks -----------------------"
        )
        node_valid = self.validate_node_keys()
        rate_valid = self.validate_rate_keys()
        chainquery_valid = self.validate_chain_query_keys()

        if not (node_valid and rate_valid and chainquery_valid):
            logger.error("Configuration validation failed.")
            logger.info(
                "-------------------- Configuration Validation Failed ------------------"
            )
            return False
        logger.info(
            "-------------------- Configuration Validation Passed ------------------"
        )
        return True
