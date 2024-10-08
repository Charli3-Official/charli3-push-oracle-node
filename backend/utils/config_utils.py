"""Utility functions for configuration handling."""

import logging
import os
import re
from typing import Dict, NamedTuple

import yaml
from pycardano import Address

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RewardCollectionConfig(NamedTuple):
    """Configuration for the reward collection service."""

    destination_address: Address
    trigger_amount: int  # in lovelace


# Load Configuration
def load_config(config_path="config.yml") -> Dict:
    """
    Load the configuration from the specified file path, handling includes and placeholders.
    config.yml takes priority over the included dynamic_config.yml.
    """
    logger.info("Loading configuration from %s", config_path)
    config = load_yaml_file(config_path)

    # Handle included configurations if present
    if "include" in config:
        included_config_path = config["include"]
        logger.info("Loading dynamic configuration from %s", included_config_path)
        dynamic_config = load_yaml_file(included_config_path)

        # Merge configurations, with config taking priority
        merged_config = merge_configs(dynamic_config, config)
        logger.info("Merged main and dynamic configurations")

        # Remove the 'include' key from the merged config
        merged_config.pop("include", None)
    else:
        merged_config = config

    # Resolve placeholders using the combined configuration
    replace_placeholders(merged_config, merged_config)

    # Warn about conflicting values
    warn_conflicting_values(config, dynamic_config if "include" in config else {})

    return merged_config


def load_yaml_file(file_path):
    """Helper function to load a YAML file."""
    with open(file_path, "r", encoding="UTF-8") as file:
        return yaml.safe_load(file)


def merge_configs(base_config, override_config):
    """Recursively merge two configurations, with override_config taking priority."""
    merged = base_config.copy()
    for key, value in override_config.items():
        if isinstance(value, dict) and key in merged and isinstance(merged[key], dict):
            merged[key] = merge_configs(merged[key], value)
        else:
            merged[key] = value
    return merged


def replace_placeholders(config, dynamic_values):
    """Recursively replace placeholders in the configuration, if any."""
    if isinstance(config, dict):
        for key, value in config.items():
            if isinstance(value, dict):
                replace_placeholders(value, dynamic_values)
            elif isinstance(value, str):
                config[key] = resolve_placeholder(value, dynamic_values)
    elif isinstance(config, list):
        for i, item in enumerate(config):
            if isinstance(item, (dict, list, str)):
                config[i] = (
                    replace_placeholders(item, dynamic_values)
                    if isinstance(item, (dict, list))
                    else resolve_placeholder(item, dynamic_values)
                )
    return config


def resolve_placeholder(value, dynamic_values):
    """Resolve a single placeholder string."""
    pattern = r"<%=\s*@(\w+)\s*%>"
    match = re.search(pattern, value)
    if match:
        placeholder = match.group(1)
        return dynamic_values.get(
            placeholder, value
        )  # Return the value if found, else the original string
    return value


def load_env_vars(name: str, config: dict):
    """
    Load environment variables based on the keys in the given config section.

    Args:
        name (str): The key in the config dictionary for which the environment
                    variables will be set.
        config (Dict): The configuration dictionary.
    """
    if name not in config:
        raise ValueError(f"Key '{name}' not found in the configuration")

    section_config = config[name]
    for key, value in section_config.items():
        env_key = key.upper()
        os.environ[env_key] = str(value)


def warn_conflicting_values(config: Dict, dynamic_config: Dict):
    """Warn users if there are conflicting values between the two files,
    showing which value will be used."""
    for key, value in dynamic_config.items():
        if key in config and config[key] != value:
            logger.warning(
                "Conflicting value for '%s'. Using value from config.yml: %s",
                key,
                config[key],
            )
