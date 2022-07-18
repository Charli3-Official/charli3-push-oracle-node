"""Node contract class testing file"""

import json
from unittest import mock

import pytest
import sure # pylint: disable=unused-import
from mocket import async_mocketize
from mocket.plugins.httpretty import httpretty
from backend.api.node import PABTimeout

from backend.core import Oracle
from backend.api import NodeContractApi

# Variables
MOCK_PAB_URL = "http://localhost:9080/api"
MOCK_CONTRACT_ID = "contract_id"
MOCK_NODE_WID = "NodeWalletId"
MOCK_NODE_PKH = "NodePKH"
MOCK_OWNER_PKH = "OwnerPKH"
MOCK_ORACLE_CURR = "OracleCurr"
MOCK_CHARLI3_TOKEN = ("Charli3Curr", "Charli3Tkn")
MOCK_TXID = "MockLastTxId"
MOCK_UPDATE_AMMOUNT = 123

# Mock classes
MOCK_ORACLE = Oracle(
    MOCK_OWNER_PKH,
    MOCK_ORACLE_CURR,
    MOCK_CHARLI3_TOKEN
)

@pytest.mark.asyncio
class TestNode():
    """Test class for all the required http methods"""

    def _register_uri(self, path, body, method="POST"):
        """Helper method to mock http endpoints"""
        httpretty.register_uri(
            getattr(httpretty, method),
            f"{MOCK_PAB_URL}{path}",
            body=json.dumps(body),
            **{"Content-Type": "application/json"}
        )

    def _register_endpoint(self, node, name):
        self._register_uri(
            f"/contract/instance/{node.contract_id}/endpoint/{name}",
            [])
        self._register_uri(
            f"/contract/instance/{node.contract_id}/status",
            gen_mock_status(name),
            "GET"
        )

    async def _init_contract(self):
        self._register_uri(
            "/contract/activate",
            MOCK_ACTIVATE
        )

        status = 'active'
        self._register_uri(
            f"/contract/instances?status={status}",
            MOCK_ACTIVE_INSTANCES,
            'GET'
        )

        node_api = NodeContractApi(
            MOCK_ORACLE,
            MOCK_NODE_WID,
            MOCK_NODE_PKH,
            MOCK_PAB_URL
        )
        await node_api.activate()
        return node_api

    @async_mocketize(strict_mode=True)
    async def test_node_activate(self):
        """Test the activation method"""
        node_api = await self._init_contract()

        node_api.contract_id.should.equal(MOCK_CONTRACT_ID)

        lareq = httpretty.last_request
        lareq.method.should.equal("POST")
        lareq.body.should.contain(bytes(MOCK_NODE_WID, encoding="utf-8"))
        lareq.body.should.contain(bytes(MOCK_ORACLE.to_json(),
                                        encoding="utf-8"))

    @async_mocketize(strict_mode=True)
    async def test_node_update(self):
        """Test the update method"""
        node_api = await self._init_contract()
        self._register_endpoint(node_api, "node-update")

        with mock.patch('asyncio.sleep', new_callable=AsyncMock):
            await node_api.update(MOCK_UPDATE_AMMOUNT)

        endpoint_req = httpretty.latest_requests[-2]
        endpoint_req.method.should.equal("POST")
        endpoint_req.body.should.equal(bytes(str(MOCK_UPDATE_AMMOUNT),
                                             encoding="utf-8"))

    @async_mocketize(strict_mode=True)
    async def test_node_aggregate(self):
        """Test the aggregate operation"""
        node_api = await self._init_contract()
        self._register_endpoint(node_api, "aggregate")

        with mock.patch('asyncio.sleep', new_callable=AsyncMock):
            await node_api.aggregate()

        endpoint_req = httpretty.latest_requests[-2]
        endpoint_req.method.should.equal("POST")
        endpoint_req.body.should.equal(b"[]")

    @async_mocketize(strict_mode=True)
    async def test_node_update_aggregate(self):
        """Test the update aggregate operation"""
        node_api = await self._init_contract()
        self._register_endpoint(node_api, "update-aggregate")

        with mock.patch('asyncio.sleep', new_callable=AsyncMock):
            await node_api.update_aggregate(MOCK_UPDATE_AMMOUNT)

        endpoint_req = httpretty.latest_requests[-2]
        endpoint_req.method.should.equal("POST")
        endpoint_req.body.should.equal(bytes(str(MOCK_UPDATE_AMMOUNT),
                                             encoding="utf-8"))

    @async_mocketize(strict_mode=True)
    async def test_node_collect(self):
        """Test the collect operation"""
        node_api = await self._init_contract()
        self._register_endpoint(node_api, "node-collect")

        with mock.patch('asyncio.sleep', new_callable=AsyncMock):
            await node_api.collect()

        endpoint_req = httpretty.latest_requests[-2]
        endpoint_req.method.should.equal("POST")
        endpoint_req.body.should.equal(b"[]")

    @async_mocketize(strict_mode=True)
    async def test_node_status(self):
        """Test the status endpoint call"""
        node_api = await self._init_contract()
        self._register_uri(
            f"/contract/instance/{node_api.contract_id}/status",
            gen_mock_status("update"),
            "GET"
        )

        await node_api.status()

        endpoint_req = httpretty.last_request
        endpoint_req.method.should.equal("GET")
        endpoint_req.body.should.equal(b"")

    @async_mocketize(strict_mode=True)
    async def test_node_stop(self):
        """Test the contract stop endpoint"""
        node_api = await self._init_contract()
        self._register_uri(
            f"/contract/instance/{node_api.contract_id}/stop",
            "[]",
            "PUT"
        )

        await node_api.stop()

        endpoint_req = httpretty.last_request
        endpoint_req.method.should.equal("PUT")
        endpoint_req.body.should.equal(b"")

    @async_mocketize(strict_mode=True)
    async def test_endpoint_timeout(self):
        """Test the timeout exception"""
        failed = False
        operation = "node-update"
        node_api = await self._init_contract()
        self._register_uri(
            f"/contract/instance/{node_api.contract_id}/endpoint/{operation}",
            [])
        self._register_uri(
            f"/contract/instance/{node_api.contract_id}/status",
            gen_mock_empty_status(operation),
            "GET"
        )
        with mock.patch('asyncio.sleep', new_callable=AsyncMock):
            try:
                await node_api.update(MOCK_UPDATE_AMMOUNT)
            except PABTimeout:
                failed = True
        assert failed

# Mock responses
MOCK_ACTIVATE = {
    "unContractInstanceId": MOCK_CONTRACT_ID
}

#MOCK_ACTIVE_INSTANCES
MOCK_ACTIVE_INSTANCES = []

# We keep this response to only the part we are interested ot prevent the file
# getting to big
def gen_mock_status(operation):
    """Generate a succesful status for an operation"""
    return {
        "cicCurrentState": {
            "observableState": {
                "status": {
                    "contents": {
                        "getTxId": MOCK_TXID
                    },
                    "tag": "LastTx"
                },
                "operation": operation
            }
        }
    }

def gen_mock_empty_status(operation):
    """Generate a succesful status for an operation"""
    return {
        "cicCurrentState": {
            "observableState": {
                "status": {
                    "tag": "Empty"
                },
                "operation": operation
            }
        }
    }

class AsyncMock(mock.MagicMock):
    """Mock for asyncio.sleep"""
    # pylint: disable=invalid-overridden-method
    # pylint: disable=useless-super-delegation
    async def __call__(self, *args, **kwargs):
        return super().__call__(*args, **kwargs)
