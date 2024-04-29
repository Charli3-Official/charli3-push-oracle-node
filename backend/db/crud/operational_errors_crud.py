"""Operational errors CRUD."""

from .base_crud import BaseCrud
from ..models.operational_errors import (
    OperationalError,
    OperationalErrorCreate,
    OperationalErrorUpdate,
)


class OperationalErrorsCrud(
    BaseCrud[OperationalError, OperationalErrorCreate, OperationalErrorUpdate]
):
    """Operational errors CRUD operations."""

    pass  # pylint: disable=unnecessary-pass


operational_errors_crud = OperationalErrorsCrud(OperationalError)
