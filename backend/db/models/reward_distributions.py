"""Models for reward distributions."""

from decimal import Decimal
from uuid import UUID

from sqlmodel import Field, SQLModel

from .base import BaseUUIDModel


class RewardDistributionBase(SQLModel):
    """Base model for reward distribution."""

    node_pkh: str = Field(foreign_key="node.pub_key_hash")
    total_rewards_available: Decimal
    aggregation_reward_increase: Decimal
    node_aggregation_id: UUID = Field(foreign_key="nodeaggregation.id")


class RewardDistribution(RewardDistributionBase, BaseUUIDModel, table=True):
    """Model for reward distribution."""

    pass  # pylint: disable=unnecessary-pass


class RewardDistributionCreate(RewardDistributionBase):
    """Model for creating a reward distribution."""

    pass  # pylint: disable=unnecessary-pass


class RewardDistributionUpdate(RewardDistributionBase):
    """Model for updating a reward distribution."""

    pass  # pylint: disable=unnecessary-pass
