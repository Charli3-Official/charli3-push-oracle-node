#!/usr/bin/env python3

from .api import Api

class NodeContractApi(Api):
    """Abstracts the calls to the PAB API."""
    def __init__(self, oracle, wallet_id, pkh):
        self.oracle = oracle
        self.wallet_id = wallet_id
        self.pkh = pkh
        self.activate()

    def is_activated(self):
        return hasattr(self, "contract_id") and self.contract_id is not None

    def activate(self):
        # TODO: Assigns the contract_id on the instance after activation.
        pass

    def update(self, rate):
        pass

    def aggregate(self):
        pass

    def update_aggregate(self, rate):
        pass

    def collect(self):
        pass

    def status(self):
        pass

    def stop(self):
        pass