"""Node contract class"""

import re
import asyncio

from .api import Api


def _require_activated(func):
    def wrapper(self, *args, **kwargs):
        if not self.is_activated():
            raise NotActivated("Contract not activated")
        return func(self, *args, **kwargs)
    return wrapper

def _await_status(func):
    async def wrapper(self, *args, **kwargs):
        await func(self, *args, **kwargs)
        await asyncio.sleep(1)
        resp = await self.status()
        resp = resp.json["cicCurrentState"]["observableState"]
        tries = 0
        while resp["status"]["tag"]=="Empty":
            if tries>6:
                raise PABTimeout("Operation Timed Out")
            await asyncio.sleep(10)
            resp = await self.status()
            resp = resp.json["cicCurrentState"]["observableState"]
        _check_error(resp)
    return wrapper

def _check_error(resp):
    if resp["status"]["tag"] == "Error":
        mess = resp["status"]["contents"]["contents"]["contents"]
        rege = r"\\\"message\\\":\\\"(.*?)\\\""
        match = re.findall(rege, mess, re.MULTILINE)
        raise FaliedOperation(match[0])

class NodeContractApi(Api):
    """Abstracts the calls to the PAB API."""
    api_url = "http://localhost:9080/api"

    def __init__(self, oracle, wallet_id, pkh):
        self.oracle = oracle
        self.wallet_id = wallet_id
        self.pkh = pkh
        self.contract_id = None

    def is_activated(self):
        """Returns if the instance is activated"""
        return hasattr(self, "contract_id") and self.contract_id is not None

    async def activate(self):
        """Activate the contract using the provided arguments"""
        if self.is_activated():
            return
        data = {
            "caID": {
                "tag": "ConnectNode",
                "contents":self.oracle.to_dict()
            },
            "caWallet": {
                "getWalletId": self.wallet_id
            }
        }
        print(data)
        resp = await self._request("POST", "/contract/activate", data)
        self.contract_id = resp.json["unContractInstanceId"]

    def _get_endpoint_path(self, endpoint):
        return f"/contract/instance/{self.contract_id}/endpoint/{endpoint}"

    @_require_activated
    @_await_status
    async def update(self, rate):
        """Requests the pab to update the NodeFeed"""
        await self._request(
            "POST",
            self._get_endpoint_path("node-update"),
            rate
        )

    @_require_activated
    @_await_status
    async def aggregate(self):
        """Requests the pab to aggregate the OracleFeed"""
        await self._request("POST", self._get_endpoint_path("aggregate"), [])

    @_require_activated
    @_await_status
    async def update_aggregate(self, rate):
        """Request the pab to perform an update aggregate"""
        await self._request(
            "POST",
            self._get_endpoint_path("update-aggregate"),
            rate
        )

    @_require_activated
    @_await_status
    async def collect(self):
        """Requests the pab to collect the aquired c3"""
        await self._request("POST", self._get_endpoint_path("node-collect"), [])

    @_require_activated
    async def status(self):
        """Requests the pab for the status of the contract"""
        resp = await self._request(
            "GET",
            f"/contract/instance/{self.contract_id}/status"
        )
        return resp

    @_require_activated
    async def stop(self):
        """Stops the contract"""
        await self._request(
            "PUT",
            f"/contract/instance/{self.contract_id}/stop")

class NotActivated(Exception):
    """Used when calling and endpoint while the contract is not activated"""

class FaliedOperation(Exception):
    """Used when a Contract operation fails"""

class PABTimeout(Exception):
    """Used when the PAB fails to respond in a timely manner"""
