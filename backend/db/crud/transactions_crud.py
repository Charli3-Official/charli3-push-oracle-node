"""Transactions CRUD operations."""

from ..models.transactions import Transaction, TransactionCreate, TransactionUpdate
from .base_crud import BaseCrud


class TransactionCrud(BaseCrud[Transaction, TransactionCreate, TransactionUpdate]):
    """Transactions CRUD operations."""

    pass  # pylint: disable=unnecessary-pass


transaction_crud = TransactionCrud(Transaction)
