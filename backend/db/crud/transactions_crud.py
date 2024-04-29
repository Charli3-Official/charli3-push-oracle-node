"""Transactions CRUD operations."""

from .base_crud import BaseCrud
from ..models.transactions import Transaction, TransactionCreate, TransactionUpdate


class TransactionCrud(BaseCrud[Transaction, TransactionCreate, TransactionUpdate]):
    """Transactions CRUD operations."""

    pass  # pylint: disable=unnecessary-pass


transaction_crud = TransactionCrud(Transaction)
