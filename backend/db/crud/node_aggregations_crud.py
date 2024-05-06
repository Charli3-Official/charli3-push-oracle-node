"""Node Operation CRUD Operations"""

from ..models.node_aggregations import (
    NodeAggregation,
    NodeAggregationCreate,
    NodeAggregationUpdate,
)
from .base_crud import BaseCrud


class NodeOperationCrud(
    BaseCrud[NodeAggregation, NodeAggregationCreate, NodeAggregationUpdate]
):
    """Node Operation CRUD operations."""

    pass  # pylint: disable=unnecessary-pass


node_aggregation_crud = NodeOperationCrud(NodeAggregation)
