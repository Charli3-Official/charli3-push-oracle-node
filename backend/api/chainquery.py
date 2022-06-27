#!/usr/bin/env python3
"""Abstracts the calls to the chain index API."""
from .api import Api
from .datums import NodeDatum, OracleDatum


class ChainQuery(Api):
    """chainQuery methods"""
    api_url = "http://54.219.17.88:7081/"

    async def get_currency_utxos(self, nft: tuple[str, str]) -> list[dict]:
        """Get utxos list from the nft currency symbol."""
        query_path = "utxo-with-currency"
        req = {
            "currency": {
                "unAssetClass": [
                    {
                        "unCurrencySymbol": nft[0]
                    },
                    {
                        "unTokenName": nft[1]
                    }
                ]
            }
        }
        resp = await self._request(
            'POST',
            query_path,
            req,
        )
        if (200 <= resp.status and resp.status < 300):
            return resp.json['page']['pageItems']
        else:
            return None

    async def get_datum(self, utxo):
        """Get Datum from utxo"""
        query_path = "unspent-tx-out"
        resp = await self._request(
            'POST',
            query_path,
            utxo,
        )
        if (200 <= resp.status and resp.status < 300):
            data = resp.json['_ciTxOutDatum']
            if "Right" in data:
                return data['Right']
            if "Left" in data:
                return await self.get_datum_from_hash(data['Left'])
        else:
            return None

    async def get_datum_from_hash(self, datum_hash):
        """Get Datum from hash"""
        query_path = "from-hash/datum"
        resp = await self._request(
            'POST',
            query_path,
            datum_hash,
        )
        if (200 <= resp.status and resp.status < 300):
            return resp.json
        else:
            return None

    async def get_oracle_datum(self, oracle_nft):
        """Get Oracle Datum from Oracle utxo"""
        utxo = await self.get_currency_utxos(oracle_nft)
        if len(utxo) > 0 :
            datum = await self.get_datum(utxo[0])
            if datum != "":
                return OracleDatum(datum)

    async def get_nodes_datum(self, node_nft):
        """Get Node Datum list from Node utxos"""
        result = []
        utxos = await self.get_currency_utxos(node_nft)
        if len(utxos) > 0 :
            for utxo in utxos:
                node_datum = await self.get_datum(utxo)
                if node_datum != "":
                    result.append(NodeDatum(node_datum))
        return result

    def get_tx_status(self, txid):
        """Get Tx status"""
