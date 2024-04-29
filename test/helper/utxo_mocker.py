""" Helper to build pycardano and blockfrost classes """

import json
from types import SimpleNamespace
from typing import List

from pycardano import (
    Address,
    Asset,
    AssetName,
    DatumHash,
    MultiAsset,
    RawCBOR,
    ScriptHash,
    TransactionInput,
    TransactionOutput,
    UTxO,
    Value,
)

SCRIPT_HASH_SIZE = 28


class Namespace(SimpleNamespace):
    """Used by flockfrots to give namespaces formatted output"""

    def to_dict(self):
        """Namespace as dictionary"""
        return self.__dict__

    def to_json(self):
        """Namespace as json"""
        return json.dumps(self.to_dict())


def convert_json_to_object(json_response):
    """Converts a dictionary in a class"""
    json_response = json.dumps(json_response)

    return json.loads(json_response, object_hook=lambda d: Namespace(**d))


def utxo_mocker(address, response):
    """Converst api address utxos from blockfrost in pycardano classess"""

    def py_utxos(address: str, results) -> List[UTxO]:
        utxos = []

        for result in results:
            tx_in = TransactionInput.from_primitive(
                [result.tx_hash, result.output_index]
            )
            amount = result.amount
            lovelace_amount = 0
            multi_assets = MultiAsset()
            for item in amount:
                if item.unit == "lovelace":
                    lovelace_amount = int(item.quantity)
                else:
                    # The utxo contains Multi-asset
                    data = bytes.fromhex(item.unit)
                    policy_id = ScriptHash(data[:SCRIPT_HASH_SIZE])
                    asset_name = AssetName(data[SCRIPT_HASH_SIZE:])

                    if policy_id not in multi_assets:
                        multi_assets[policy_id] = Asset()
                    multi_assets[policy_id][asset_name] = int(item.quantity)

            amount = Value(lovelace_amount, multi_assets)

            datum_hash = (
                DatumHash.from_primitive(result.data_hash)
                if result.data_hash and result.inline_datum is None
                else None
            )

            datum = None

            if hasattr(result, "inline_datum") and result.inline_datum is not None:
                datum = RawCBOR(bytes.fromhex(result.inline_datum))

            script = None

            if (
                hasattr(result, "reference_script_hash")
                and result.reference_script_hash
            ):
                script = ""

            tx_out = TransactionOutput(
                Address.from_primitive(address),
                amount=amount,
                datum_hash=datum_hash,
                datum=datum,
                script=script,
            )
            utxos.append(UTxO(tx_in, tx_out))

        return utxos

    return py_utxos(address, convert_json_to_object(response))
