#!/usr/bin/env python3
"""Abstracts the calls to the chain index API."""
import logging
from .api import Api
from .datums import NodeDatum, OracleDatum

logger = logging.getLogger("ChainQuery")

class ChainQuery(Api):
    """chainQuery methods"""
    def __init__(self, api_url):
        self.api_url = api_url

    async def get_currency_utxos(self, nft: tuple[str, str]) -> list[dict]:
        """Get utxos list from the nft currency symbol."""
        logger.info("Getting utxos with %s", nft)
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
        if resp.is_ok:
            utxos = resp.json['page']['pageItems']
            logger.debug("Utxos: %s",utxos)
            return utxos
        return None

    async def get_datum(self, utxo):
        """Get Datum from utxo"""
        query_path = "unspent-tx-out"
        resp = await self._request(
            'POST',
            query_path,
            utxo,
        )
        if resp.is_ok:
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
        if resp.is_ok:
            return resp.json
        return None

    async def get_oracle_datum(self, oracle_nft):
        """Get Oracle Datum from Oracle utxo"""
        logger.info("Getting oracle datum for %s", oracle_nft[0])
        utxo = await self.get_currency_utxos(oracle_nft)
        if len(utxo) > 0 :
            datum = await self.get_datum(utxo[0])
            if datum != "":
                return OracleDatum(datum)

    async def get_nodes_datum(self, node_nft):
        """Get Node Datum list from Node utxos"""
        logger.info("Getting node datums for %s", node_nft[0])
        result = []
        utxos = await self.get_currency_utxos(node_nft)
        if len(utxos) > 0 :
            for utxo in utxos:
                node_datum = await self.get_datum(utxo)
                if node_datum != "":
                    result.append(NodeDatum(node_datum))
        logger.debug("Found %d nodes", len(result))
        return result

    def get_tx_status(self, txid):
        """Get Tx status"""
