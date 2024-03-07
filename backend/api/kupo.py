"""Kupo"""
from typing import Optional, Union, Tuple, List
from cachetools import LRUCache

import pycardano as pyc
import requests
import cbor2


class Kupo:
    """Kupo Class"""

    def __init__(self):
        # self.kupo_url = "https://dmtr_kupo1vae8q3nexf3y56tvvfcnx5mvta44qn62f9mscrg7a9.preprod-v2.kupo-m1.demeter.run"
        self.kupo_url = "http://localhost:1442"
        self.datum_cache = LRUCache(maxsize=100)

    def _try_fix_script(
        self, scripth: str, script: Union[pyc.PlutusV1Script, pyc.PlutusV2Script]
    ) -> Union[pyc.PlutusV1Script, pyc.PlutusV2Script]:
        if str(pyc.script_hash(script)) == scripth:
            return script
        new_script = script.__class__(cbor2.loads(script))
        if str(pyc.script_hash(new_script)) == scripth:
            return new_script
        raise ValueError("Cannot recover script from hash.")

    def _extract_asset_info(
        self,
        asset_hash: str,
    ) -> Tuple[str, pyc.ScriptHash, pyc.AssetName]:  # noqa
        split_result = asset_hash.split(".")

        if len(split_result) == 1:
            policy_hex, asset_name_hex = split_result[0], ""
        elif len(split_result) == 2:
            policy_hex, asset_name_hex = split_result
        else:
            raise ValueError(f"Unable to parse asset hash: {asset_hash}")

        policy = pyc.ScriptHash.from_primitive(policy_hex)
        asset_name = pyc.AssetName.from_primitive(asset_name_hex)

        return policy_hex, policy, asset_name

    def _get_datum_from_kupo(self, datum_hash: str) -> Optional[pyc.RawCBOR]:
        """Get datum from Kupo.

        Args:
            datum_hash (str): A datum hash.

        Returns:
            Optional[RawCBOR]: A datum.
        """
        datum = self.datum_cache.get(datum_hash, None)

        if datum is not None:
            return datum

        if self.kupo_url is None:
            raise AssertionError(
                "kupo_url object attribute has not been assigned properly."
            )

        kupo_datum_url = self.kupo_url + "/datums/" + datum_hash
        datum_result = requests.get(kupo_datum_url).json()
        if datum_result and datum_result["datum"] != datum_hash:
            datum = pyc.RawCBOR(bytes.fromhex(datum_result["datum"]))

        self.datum_cache[datum_hash] = datum
        return datum

    def utxos_kupo(self, address: str) -> List[pyc.UTxO]:
        """Get all UTxOs associated with an address with Kupo.
        Since UTxO querying will be deprecated from Ogmios in next
        major release: https://ogmios.dev/mini-protocols/local-state-query/.

        Args:
            address (str): An address encoded with bech32.

        Returns:
            List[UTxO]: A list of UTxOs.
        """
        if self.kupo_url is None:
            raise AssertionError(
                "kupo_url object attribute has not been assigned properly."
            )

        kupo_utxo_url = self.kupo_url + "/matches/" + address + "?unspent"
        results = requests.get(kupo_utxo_url).json()

        utxos = []

        for result in results:
            tx_id = result["transaction_id"]
            index = result["output_index"]

            if result["spent_at"] is None:
                tx_in = pyc.TransactionInput.from_primitive([tx_id, index])

                lovelace_amount = result["value"]["coins"]

                script = None
                script_hash = result.get("script_hash", None)
                if script_hash:
                    kupo_script_url = self.kupo_url + "/scripts/" + script_hash
                    script = requests.get(kupo_script_url).json()
                    if script["language"] == "plutus:v2":
                        script = pyc.PlutusV2Script(
                            bytes.fromhex(script["script"])
                        )  # noqa
                        script = self._try_fix_script(script_hash, script)
                    elif script["language"] == "plutus:v1":
                        script = pyc.PlutusV1Script(
                            bytes.fromhex(script["script"])
                        )  # noqa
                        script = self._try_fix_script(script_hash, script)
                    else:
                        raise ValueError("Unknown plutus script type")

                datum = None
                datum_hash = (
                    pyc.DatumHash.from_primitive(result["datum_hash"])
                    if result["datum_hash"]
                    else None
                )
                if datum_hash and result.get("datum_type", "inline"):
                    datum = self._get_datum_from_kupo(result["datum_hash"])

                if not result["value"]["assets"]:
                    tx_out = pyc.TransactionOutput(
                        pyc.Address.from_primitive(address),
                        amount=lovelace_amount,
                        datum_hash=datum_hash,
                        datum=datum,
                        script=script,
                    )
                else:
                    multi_assets = pyc.MultiAsset()

                    for asset, quantity in result["value"]["assets"].items():
                        policy_hex, policy, asset_name_hex = self._extract_asset_info(
                            asset
                        )
                        multi_assets.setdefault(policy, pyc.Asset())[
                            asset_name_hex
                        ] = quantity

                    tx_out = pyc.TransactionOutput(
                        pyc.Address.from_primitive(result["address"]),
                        amount=pyc.Value(lovelace_amount, multi_assets),
                        datum_hash=datum_hash,
                        datum=datum,
                        script=script,
                    )
                utxos.append(pyc.UTxO(tx_in, tx_out))
            else:
                continue

        return utxos
