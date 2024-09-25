"""Utility functions for configuration handling."""

import os
import re
from typing import Dict, NamedTuple

import yaml
from pycardano import Address


class RewardCollectionConfig(NamedTuple):
    """Configuration for the reward collection service."""

    destination_address: Address
    trigger_amount: int  # in lovelace


# Load Configuration
def load_config(config_path="config.yml") -> Dict:
    """Load the configuration from the specified file path, handling includes and placeholders"""
    config = load_yaml_file(config_path)

    # Handle included configurations if present
    if "include" in config:
        included_config_path = config["include"]
        additional_config = load_yaml_file(included_config_path)
        merge_configs(config, additional_config)
        config.pop("include", None)  # Optionally remove the 'include' key

    # Resolve placeholders using the combined configuration, if any
    replace_placeholders(config, config)

    return config


def load_yaml_file(file_path):
    """Helper function to load a YAML file."""
    with open(file_path, "r", encoding="UTF-8") as file:
        return yaml.safe_load(file)


def merge_configs(base_config, additional_config):
    """Recursively merge two configurations."""
    if isinstance(additional_config, dict):
        for key, value in additional_config.items():
            if key in base_config and isinstance(base_config[key], dict):
                merge_configs(base_config[key], value)
            else:
                base_config[key] = value


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
