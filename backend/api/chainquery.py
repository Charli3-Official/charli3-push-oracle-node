#!/usr/bin/env python3
"""Abstracts the calls to the chain index API."""
import logging
from base64 import b16encode

from blockfrost import BlockFrostApi

from .api import Api
from .datums import NodeDatum, OracleDatum

logger = logging.getLogger("ChainQuery")

class ChainQuery(Api):
    """ Chain Query Abstract Methods """
    async def get_oracle_datum(self, oracle_nft):
        """Get Oracle Datum from Oracle utxo"""

    async def get_nodes_datum(self, node_nft):
        """Get Node Datum list from Node utxos"""


class ChainQueryIndex(ChainQuery):
    """chainQuery PAB Methods"""
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
        resp = await self._post(
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
        resp = await self._post(
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
        resp = await self._post(
            query_path,
            datum_hash,
        )
        if resp.is_ok:
            return resp.json
        return None

    async def get_oracle_datum(self, oracle_nft):
        logger.info("Getting oracle datum for %s", oracle_nft[0])
        utxo = await self.get_currency_utxos(oracle_nft)
        if len(utxo) > 0 :
            datum = await self.get_datum(utxo[0])
            if datum != "":
                return OracleDatum.from_cbor(datum)

    async def get_nodes_datum(self, node_nft):
        logger.info("Getting node datums for %s", node_nft[0])
        result = []
        utxos = await self.get_currency_utxos(node_nft)
        if len(utxos) > 0 :
            for utxo in utxos:
                node_datum = await self.get_datum(utxo)
                if node_datum != "":
                    result.append(NodeDatum.from_cbor(node_datum))
        logger.debug("Found %d nodes", len(result))
        return result

    def get_tx_status(self, txid):
        """Get Tx status"""



class ChainQueryBlockfrost(ChainQuery):
    """chainQuery methods"""
    def __init__(self, token, api_url):
        self.api = BlockFrostApi(
            project_id=token,
            base_url=api_url,
        )

    def _get_datum(self, utxo):
        return self.api.script_datum(utxo.data_hash).json_value

    def _get_blockfrost_asset(self, asset):
        return asset[0]+str(
            b16encode(bytes(
                asset[1],
                encoding="utf-8")
            ), encoding="utf-8"
        ).lower()

    def _get_asset_utxo(self, asset):
        asset = self._get_blockfrost_asset(asset)
        addr = self.api.asset_addresses(asset)[0].address
        return self.api.address_utxos_asset(addr, asset)

    async def get_oracle_datum(self, oracle_nft):
        """Get Oracle Datum from Oracle utxo"""
        logger.info("Getting oracle datum for %s", oracle_nft[0])
        utxo = self._get_asset_utxo(oracle_nft)
        if len(utxo) > 0 :
            datum = self._get_datum(utxo[0])
            return OracleDatum.from_blockfrost(datum)

    async def get_nodes_datum(self, node_nft):
        """Get Node Datum list from Node utxos"""
        logger.info("Getting node datums for %s", node_nft[0])
        result = []
        asset = self._get_blockfrost_asset(node_nft)
        addr = self.api.asset_addresses(asset)[0].address
        utxos = self.api.address_utxos_asset(addr, asset)
        if len(utxos) > 0:
            for utxo in utxos:
                node_datum = self._get_datum(utxo)
                result.append(NodeDatum.from_blockfrost(node_datum))
        logger.debug("Found %d nodes", len(result))
        return result

chainQueryTypes = {
    "blockfrost": ChainQueryBlockfrost,
    "chain-index": ChainQueryIndex
}
