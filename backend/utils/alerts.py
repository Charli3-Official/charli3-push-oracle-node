"""Alert manager module"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, TypedDict, Union

import apprise
from apprise import AppriseAsset, NotifyFormat, NotifyType
from charli3_offchain_core.chain_query import ChainQuery
from pycardano import Network

logger = logging.getLogger(__name__)


class AlertConfig(TypedDict):
    """Base alert configuration"""

    cooldown: int
    thresholds: Dict[str, Union[int, float]]


class NotificationConfig(TypedDict):
    """Notification configuration"""

    type: str
    config: Dict[str, str]


@dataclass
class Thresholds:
    """Thresholds for alerts"""

    c3_token_balance: float  # In whole C3 tokens
    ada_balance: float  # In ADA
    minimum_data_sources: int
    timeout_variance: float  # In percentage


class AlertManager:
    """Alert manager class"""

    DEFAULT_THRESHOLDS = Thresholds(
        c3_token_balance=50.0,
        ada_balance=50.0,
        minimum_data_sources=3,
        timeout_variance=105.0,
    )

    def __init__(
        self,
        feed_name: str,
        chain_query: ChainQuery,
        alert_config: AlertConfig,
        notification_configs: List[NotificationConfig],
        network: Network,
        min_requirement: bool = True,
    ):
        self.feed_name = feed_name
        self.chain_query = chain_query
        self.cooldown = alert_config.get("cooldown", 1800)  # Default 30 minutes
        self.network = network
        self.min_requirement = min_requirement

        # Merge default thresholds with custom thresholds
        custom_thresholds = alert_config.get("thresholds", {})
        self.thresholds = Thresholds(
            c3_token_balance=custom_thresholds.get(
                "c3_token_balance", self.DEFAULT_THRESHOLDS.c3_token_balance
            ),
            ada_balance=custom_thresholds.get(
                "ada_balance", self.DEFAULT_THRESHOLDS.ada_balance
            ),
            minimum_data_sources=custom_thresholds.get(
                "minimum_data_sources", self.DEFAULT_THRESHOLDS.minimum_data_sources
            ),
            timeout_variance=custom_thresholds.get(
                "timeout_variance", self.DEFAULT_THRESHOLDS.timeout_variance
            ),
        )

        # Create custom AppriseAsset
        self.asset = AppriseAsset(
            app_id="Charli3",
            app_desc="Charli3 Node Operator Alerts",
            app_url="https://charli3.io",
        )

        self.apprise = apprise.Apprise(asset=self.asset)
        self._setup_notifications(notification_configs)

        self.last_alert_times: Dict[str, int] = {}

    def _setup_notifications(self, notification_configs: List[NotificationConfig]):
        """Setup notification services based on configuration"""
        for config in notification_configs:
            if config["type"] == "slack":
                self.apprise.add(f"slack://{config['config']['webhook_url']}")
            elif config["type"] == "discord":
                self.apprise.add(f"discord://{config['config']['webhook_url']}")
            elif config["type"] == "telegram":
                self.apprise.add(
                    f"tgram://{config['config']['bot_token']}/{config['config']['chat_id']}"
                )

        logger.info(
            "Initialized AlertManager with %d notification services", len(self.apprise)
        )

    async def check_c3_token_balance(self, balance: int, script_address: str) -> None:
        """Check C3 token balance and send alert if below threshold"""
        balance_c3 = balance / 1_000_000
        if balance_c3 < self.thresholds.c3_token_balance:
            await self.send_alert(
                "Low C3 Token Balance",
                f"*Balance*: *{balance_c3:.2f} C3*\n*Threshold*: {self.thresholds.c3_token_balance} C3\n*Script Address*: {script_address}",
            )

    async def check_ada_balance(self, balance: int, address: str) -> None:
        """Check ADA balance and send alert if below threshold"""
        balance_ada = balance / 1_000_000
        if balance_ada < self.thresholds.ada_balance:
            await self.send_alert(
                "Low ADA Balance",
                f"*Balance*: *{balance_ada:.2f} ADA*\n*Threshold*: {self.thresholds.ada_balance} ADA\n*Node Address*: {address}",
            )

    async def check_aggregation_timeout(
        self, last_aggregation_time: int, aggregate_time: int
    ) -> None:
        """Check aggregation timeout and send alert if expired"""
        timeout = self._calculate_timeout(aggregate_time)
        current_time = self.chain_query.get_current_posix_chain_time_ms()
        time_since_last = current_time - last_aggregation_time
        if time_since_last > timeout:
            await self.send_alert(
                "Aggregation Timeout",
                f"*No aggregation for* *{time_since_last / 60000:.2f} minutes*\n*Last aggregation*: {self._format_time(last_aggregation_time)}\n*Timeout threshold*: {timeout / 60000:.2f} minutes",
            )

    async def check_node_update_timeout(
        self,
        last_update_time: int,
        node_expiry: int,
        node_address: str,
        is_waiting_for_optimal_update: bool = False,
        oracle_feed_data=None,
    ) -> None:
        """Check node update timeout and send alert if expired"""
        timeout = self._calculate_timeout(node_expiry)
        current_time = self.chain_query.get_current_posix_chain_time_ms()
        time_since_last = current_time - last_update_time

        # If node is waiting for optimal update timing, use extended timeout
        if is_waiting_for_optimal_update and oracle_feed_data is not None:
            # Calculate when the next aggregation is expected to occur
            aggregation_interval = (
                node_expiry  # os_updated_node_time roughly equals os_aggregate_time
            )
            next_agg_time_ms = oracle_feed_data.get_timestamp() + aggregation_interval

            # Add a reasonable buffer after the next aggregation time
            # If the node doesn't update by then, it missed its opportunity
            buffer_time = 2 * 60 * 1000  # 2 minutes buffer after next aggregation
            extended_timeout_until = next_agg_time_ms + buffer_time

            # Calculate how long that is from the last update time
            extended_timeout = extended_timeout_until - last_update_time

            # Use the longer of standard timeout or time until next aggregation + buffer
            extended_timeout = max(timeout, extended_timeout)

            logger.debug(
                f"Node waiting for optimal update. Extended timeout: {extended_timeout / 60000:.2f} min "
                f"(until next aggregation + buffer) (original: {timeout / 60000:.2f} min)"
            )

            if time_since_last > extended_timeout:
                await self.send_alert(
                    "Node Update Timeout",
                    f"*No update for* *{time_since_last / 60000:.2f} minutes*\n*Node*: {node_address}\n*Last update*: {self._format_time(last_update_time)}\n*Next aggregation expected*: {self._format_time(next_agg_time_ms)}\n*Timeout threshold*: {extended_timeout / 60000:.2f} minutes\n*Note*: Node was waiting for optimal update timing but missed the next aggregation window",
                )
        else:
            # Standard timeout check
            if time_since_last > timeout:
                await self.send_alert(
                    "Node Update Timeout",
                    f"*No update for* *{time_since_last / 60000:.2f} minutes*\n*Node*: {node_address}\n*Last update*: {self._format_time(last_update_time)}\n*Timeout threshold*: {timeout / 60000:.2f} minutes",
                )

    async def check_minimum_data_sources(
        self, active_sources: int, rate_type: str
    ) -> None:
        """Check minimum data sources and send alert if below threshold"""
        try:
            if self.min_requirement:
                if active_sources < self.thresholds.minimum_data_sources:
                    await self.send_alert(
                        f"Insufficient {rate_type.capitalize()} Data Sources",
                        f"*Active {rate_type} sources*: *{active_sources}*\n*Minimum required*: {self.thresholds.minimum_data_sources}",
                    )
                elif active_sources == 0:
                    await self.send_alert(
                        f"No Valid {rate_type.capitalize()} Rates",
                        f"Failed to obtain any valid {rate_type} rates.",
                    )
            else:
                if active_sources == 0:
                    await self.send_alert(
                        f"No Valid {rate_type.capitalize()} Rates",
                        f"Failed to obtain any valid {rate_type} rates.",
                    )
        except Exception as e:
            logger.error("Failed to send alert for minimum data sources: %s", str(e))

    async def notify_reward_collection(
        self, success: bool, amount: float, destination: str, tx_id: str
    ):
        """Notify about the result of an automatic reward collection attempt."""
        try:
            status = "Successful" if success else "Failed"
            alert_type = f"Reward Collection {status}"

            # Determine the correct cexplorer URL based on the network
            network = "preprod." if self.network == Network.TESTNET else ""

            message = f"*Amount*: {amount:.2f} C3\n*Destination*: {destination}\n"

            if tx_id:
                cexplorer_url = f"https://{network}cexplorer.io/tx/{tx_id}"
                message += f"*Transaction*: [View on cexplorer]({cexplorer_url})\n"
            await self.send_alert(alert_type, message)
        except Exception as e:
            logger.error("Failed to send alert for reward collection: %s", str(e))

    def _format_alert_message(self, time_str: str, message: str) -> str:
        """Format the alert message for universal compatibility and conciseness"""
        return f"""

*Feed*: *{self.feed_name}*

*Time*: {time_str}

{message}

------------------------
_This is an automated alert from the Charli3 Node Operator System_
        """

    def _get_alert_emoji(self, alert_type: str) -> str:
        """Get an appropriate emoji for the alert type"""
        emoji_map = {
            "Low ADA Balance": "💰",
            "Low C3 Token Balance": "🪙",
            "Aggregation Timeout": "⏳",
            "Node Update Timeout": "🔄",
            "Insufficient Data Sources": "📊",
            "Reward Collection Successful": "✅",
            "Reward Collection Failed": "❌",
        }
        return emoji_map.get(alert_type, "⚠️")

    async def send_alert(self, alert_type: str, message: str) -> None:
        """Send a concise alert message to all configured notification services"""
        current_time = self.chain_query.get_current_posix_chain_time_ms()
        time_str = self._format_time(current_time)

        if (
            current_time - self.last_alert_times.get(alert_type, 0)
            > self.cooldown * 1000
        ):
            self.last_alert_times[alert_type] = current_time

            formatted_message = self._format_alert_message(time_str, message)
            emoji = self._get_alert_emoji(alert_type)

            logger.error("ALERT - %s: %s", alert_type, formatted_message)

            notify_type = self._get_notify_type(alert_type)

            # Use Apprise to send notifications
            result = await self.apprise.async_notify(
                body=formatted_message,
                title=f"{emoji} Charli3 Alert: {alert_type} {emoji}",
                notify_type=notify_type,
                body_format=NotifyFormat.TEXT,
            )

            if result:
                logger.info("Successfully sent alert to all configured services")
            else:
                logger.error("Failed to send alert to one or more services")
        else:
            logger.info("Suppressed repeated alert for %s at %s", alert_type, time_str)

    def _get_notify_type(self, alert_type: str) -> NotifyType:
        """Map alert types to Apprise NotifyType"""
        type_map = {
            "Low ADA Balance": NotifyType.WARNING,
            "Low C3 Token Balance": NotifyType.WARNING,
            "Aggregation Timeout": NotifyType.FAILURE,
            "Node Update Timeout": NotifyType.FAILURE,
            "Insufficient Data Sources": NotifyType.WARNING,
            "Reward Collection Successful": NotifyType.SUCCESS,
            "Reward Collection Failed": NotifyType.WARNING,
        }
        return type_map.get(alert_type, NotifyType.INFO)

    def _is_expired(self, last_time: int, valid_time: int) -> bool:
        """Check if a time has expired"""
        current_time = self.chain_query.get_current_posix_chain_time_ms()
        time_elapsed = current_time - last_time
        return time_elapsed > valid_time

    def _calculate_timeout(self, base_time: int) -> int:
        """Calculate adjusted timeout based on variance"""
        return int(base_time * self.thresholds.timeout_variance / 100)

    def _format_time(self, timestamp: int) -> str:
        """Format a millisecond timestamp to a human-readable string"""
        return datetime.fromtimestamp(timestamp / 1000).strftime("%Y-%m-%d %H:%M:%S")

    async def get_address_lovelace_balance(self, address: str) -> int:
        """Get the lovelace balance of an address"""
        if self.chain_query.blockfrost_context is None:
            utxos = await self.chain_query.get_utxos(address)
            return sum(utxo.output.amount.coin for utxo in utxos)
        return await self.chain_query.get_address_balance(address)
