"""Module for validating the health of external services"""

import asyncio
import logging

import aiohttp

logger = logging.getLogger(__name__)
timeout = aiohttp.ClientTimeout(total=10)


class HealthCheckValidator:
    """Validates the health of external services like Ogmios and Kupo."""

    def __init__(self, config):
        """Initialize with config data."""
        self.config = config

    async def check_ogmios_health(
        self, session: aiohttp.ClientSession, ws_url: str, expected_network: str
    ) -> bool:
        """Check if the Ogmios service is healthy for the given ws_url."""

        health_url = ws_url.replace("ws://", "http://") + "/health"
        try:
            async with session.get(health_url) as response:
                if response.status != 200:
                    logger.error(
                        "❌ Ogmios health check failed with status code %d.",
                        response.status,
                    )
                    return False

                health_data = await response.json()
                ogmios_network = health_data.get("network", "").lower()

                # Handle network mismatch or unexpected network types
                if expected_network == "testnet":
                    if ogmios_network not in ["preprod", "preview"]:
                        logger.error(
                            "❌ Ogmios service is configured for %s network but expected testnet network.",
                            ogmios_network.upper(),
                        )
                        return False

                if ogmios_network != expected_network:
                    logger.error(
                        "❌ Ogmios service is configured for %s network but expected %s network.",
                        ogmios_network.upper(),
                        expected_network.upper(),
                    )
                    return False

                logger.info(
                    "✅ Ogmios service is healthy and matches the expected %s network.",
                    expected_network.upper(),
                )
                return True
        except asyncio.TimeoutError:
            logger.error("❌ Ogmios health check timed out.")
            return False
        except Exception as error:
            logger.error(f"Error during health check for {ws_url}: {error}")
            return False

    async def check_ogmios_or_blockfrost_health(self) -> bool:
        """Check the health of internal and external Ogmios or Blockfrost services."""
        chain_query_config = self.config.get("ChainQuery", {})
        network_config = chain_query_config.get("network", "").lower()

        ogmios_config = chain_query_config.get("ogmios", {})
        blockfrost_config = chain_query_config.get("blockfrost", {})

        external_config = chain_query_config.get("external", {})
        external_ogmios_config = external_config.get("ogmios", {})
        external_blockfrost_config = external_config.get("blockfrost", {})

        async with aiohttp.ClientSession(timeout=timeout) as session:
            health_checks = []

            # Internal check for Mainnet
            if network_config == "mainnet":
                if ogmios_config:
                    ws_url = ogmios_config.get("ws_url")
                    kupo_url = ogmios_config.get("kupo_url")
                    health_checks.append(
                        self.check_ogmios_health(session, ws_url, "mainnet")
                    )
                    health_checks.append(self._check_kupo_health(session, kupo_url))
                elif blockfrost_config:
                    logger.warning(
                        "⚠️  Blockfrost is configured, skipping health check for internal Ogmios."
                    )
                else:
                    logger.error(
                        "❌ Neither internal Ogmios nor Blockfrost is configured."
                    )
                    return False

            # External check for Testnet
            if network_config == "testnet":
                if external_ogmios_config:
                    external_ws_url = external_ogmios_config.get("ws_url")
                    external_kupo_url = external_ogmios_config.get("kupo_url")
                    health_checks.append(
                        self.check_ogmios_health(session, external_ws_url, "mainnet")
                    )
                    health_checks.append(
                        self._check_kupo_health(session, external_kupo_url)
                    )
                elif external_blockfrost_config:
                    logger.warning(
                        "⚠️  External Blockfrost is configured, skipping health check for external Ogmios."
                    )
                    return True
                else:
                    logger.error(
                        "❌ Neither external Ogmios nor Blockfrost is configured for Testnet."
                    )
                    return False

            # Run all health checks in parallel
            if health_checks:
                results = await asyncio.gather(*health_checks)
                return all(results)
            return False

    async def _check_kupo_health(
        self, session: aiohttp.ClientSession, kupo_url: str
    ) -> bool:
        """Check if the Kupo service is running using the provided Kupo URL."""
        try:
            async with session.get(kupo_url + "/health") as response:
                if response.status != 200:
                    logger.error(
                        "❌ Kupo health check failed with status code %d.",
                        response.status,
                    )
                    return False

                logger.info("✅ Kupo service is healthy.")
                return True

        except Exception as error:
            logger.error("❌ Error checking Kupo health: %s", error)
        return False

    async def run_health_checks(self) -> bool:
        """Run all the health checks for external services."""
        logger.info(
            "-------------------- Running Health Checks -----------------------"
        )

        is_healthy = await self.check_ogmios_or_blockfrost_health()

        if not is_healthy:
            logger.error("❌ One or more health checks failed.")
            logger.info(
                "-------------------- Health Checks Failed -----------------------"
            )
            return False

        logger.info("✅ All external services are healthy.")
        logger.info("-------------------- Health Checks Passed -----------------------")
        return True
