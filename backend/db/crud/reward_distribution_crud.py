"""Reward Distribution CRUD operations."""

from ..models.reward_distributions import (
    RewardDistribution,
    RewardDistributionCreate,
    RewardDistributionUpdate,
)
from .base_crud import BaseCrud


class RewardDistributionCrud(
    BaseCrud[RewardDistribution, RewardDistributionCreate, RewardDistributionUpdate]
):
    """Reward Distribution CRUD operations."""

    pass  # pylint: disable=unnecessary-pass


reward_distribution_crud = RewardDistributionCrud(RewardDistribution)
