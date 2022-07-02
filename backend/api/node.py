"""Node contract class"""

import re
import asyncio
import logging

from backend.core import Oracle
from .api import Api, UnsuccessfulResponse

logger = logging.getLogger("NodeContract")

def _log_call(func):
    def wrapper(self, *args, **kwargs):
        logger.info("Called PAB %s", func.__name__)
        return func(self, *args, **kwargs)
    return wrapper

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
        tries = 1
        while resp["status"]["tag"]=="Empty" and resp:
            if tries>=18:
                raise PABTimeout("Operation Timed Out")
            tries += 1
            await asyncio.sleep(10)
            resp = await self.status()
            resp = resp.json["cicCurrentState"]["observableState"]
        if resp["status"]["tag"] == "Error":
            _raise_error(resp)
    return wrapper

def _raise_error(resp):
    mess = resp["status"]["contents"]["contents"]["contents"]
    rege = r"\\\"message\\\":\\\"(.*?)\\\""
    match = re.findall(rege, mess, re.MULTILINE)
    raise FailedOperation(match[0])

def _catch_http_errors(func):
    async def wrapper(self, *args, **kwargs):
        try:
            resp = await func(self, *args, **kwargs)
        except UnsuccessfulResponse as e:
            raise FailedOperation(
                f"UnsuccesfulResponse from the PAB. Status={e.args[0]}"
                ) from e
        return resp
    return wrapper

class NodeContractApi(Api):
    """Abstracts the calls to the PAB API."""

    def __init__(self,
                 oracle: Oracle,
                 wallet_id: str,
                 pkh: str,
                 api_url: str):
        self.oracle = oracle
        self.wallet_id = wallet_id
        self.pkh = pkh
        self.api_url = api_url
        self.contract_id = None

    def is_activated(self):
        """Returns if the instance is activated"""
        return hasattr(self, "contract_id") and self.contract_id is not None

    def is_stuck(self):
        """Check if the PAB is broken"""
        try:
            self.status()
        except UnsuccessfulResponse:
            return True
        return False

    @_catch_http_errors
    @_log_call
    async def activate(self):
        """Activate the contract using the provided arguments"""
        if self.is_activated():
            return
        data = {
            "caID": {
                "tag": "ConnectNode",
                "contents": self.oracle.to_dict()
            },
            "caWallet": {
                "getWalletId": self.wallet_id
            }
        }
        resp = await self._request("POST", "/contract/activate", data)
        self.contract_id = resp.json["unContractInstanceId"]

    def _get_endpoint_path(self, endpoint):
        return f"/contract/instance/{self.contract_id}/endpoint/{endpoint}"

    @_require_activated
    @_await_status
    @_catch_http_errors
    @_log_call
    async def update(self, rate):
        """Requests the pab to update the NodeFeed"""
        await self._request(
            "POST",
            self._get_endpoint_path("node-update"),
            rate
        )

    @_require_activated
    @_await_status
    @_catch_http_errors
    @_log_call
    async def aggregate(self):
        """Requests the pab to aggregate the OracleFeed"""
        await self._request("POST", self._get_endpoint_path("aggregate"), [])

    @_require_activated
    @_await_status
    @_catch_http_errors
    @_log_call
    async def update_aggregate(self, rate):
        """Request the pab to perform an update aggregate"""
        await self._request(
            "POST",
            self._get_endpoint_path("update-aggregate"),
            rate
        )

    @_require_activated
    @_await_status
    @_catch_http_errors
    @_log_call
    async def collect(self):
        """Requests the pab to collect the aquired c3"""
        await self._request("POST", self._get_endpoint_path("node-collect"), [])

    @_require_activated
    @_catch_http_errors
    @_log_call
    async def status(self):
        """Requests the pab for the status of the contract"""
        resp = await self._request(
            "GET",
            f"/contract/instance/{self.contract_id}/status"
        )
        return resp

    @_require_activated
    @_catch_http_errors
    @_log_call
    async def stop(self):
        """Stops the contract"""
        await self._request(
            "PUT",
            f"/contract/instance/{self.contract_id}/stop")

class NotActivated(Exception):
    """Used when calling and endpoint while the contract is not activated"""

class FailedOperation(Exception):
    """Used when a Contract operation fails"""

class PABTimeout(Exception):
    """Used when the PAB fails to respond in a timely manner"""
