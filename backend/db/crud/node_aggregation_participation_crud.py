""" Node Aggregation Participation CRUD Operations """

from ..models.node_aggregation_participation import (
    NodeAggregationParticipation,
    NodeAggregationParticipationCreate,
    NodeAggregationParticipationUpdate,
)
from .base_crud import BaseCrud


class NodeAggregationParticipationCrud(
    BaseCrud[
        NodeAggregationParticipation,
        NodeAggregationParticipationCreate,
        NodeAggregationParticipationUpdate,
    ]
):
    """Node Aggregation Participation CRUD operations."""

    pass  # pylint: disable=unnecessary-pass


node_aggregation_participation_crud = NodeAggregationParticipationCrud(
    NodeAggregationParticipation
)
