#!/usr/bin/env python3

from .api import Api

class ChainQuery(Api):
    """Abstracts the calls to the chain explorer API."""
    def _get_currency_utxos(self, nft: tuple[str, str]) -> list[dict]:
        pass

    def get_nodes_datum(self, nft):
        pass

    def get_oracle_datum(self, nft):
        pass

    def get_tx_status(self, txid):
        pass