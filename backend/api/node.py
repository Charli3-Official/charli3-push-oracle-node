"""Node contract class"""

from .api import Api

class NodeContractApi(Api):
    """Abstracts the calls to the PAB API."""
    def __init__(self, oracle, wallet_id, pkh):
        self.oracle = oracle
        self.wallet_id = wallet_id
        self.pkh = pkh
        self.contract_id = None
        self.activate()

    def is_activated(self):
        """Returns if the instance is activated"""
        return hasattr(self, "contract_id") and self.contract_id is not None

    def activate(self):
        """Activate the contract using the provided arguments"""
        # Assigns the contract_id on the instance after activation.

    def update(self, rate):
        """Requests the pab to update the NodeFeed"""

    def aggregate(self):
        """Requests the pab to aggregate the OracleFeed"""

    def update_aggregate(self, rate):
        """Request the pab to perform an update aggregate"""

    def collect(self):
        """Requests the pab to collect the aquired c3"""

    def status(self):
        """Requests the pab for the status of the contract"""

    def stop(self):
        """Stops the contract"""
