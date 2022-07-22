"""Abstract api class testing file"""
import json

import pytest
import sure # pylint: disable=unused-import
from mocket import async_mocketize
from mocket.plugins.httpretty import httpretty

from backend.api import Api

@pytest.mark.asyncio
class TestApiMethods(Api):
    """Test class for all the required http methods"""
    api_url = "http://persodomain.com"

    @async_mocketize(strict_mode=True)
    async def test_httpbin(self):
        """Test that the values returned are correct"""
        methods = ["get", "post", "put", "delete"]
        for i in methods:
            httpretty.register_uri(
                getattr(httpretty, i.upper()),
                f"{self.api_url}/{i}",
                body=json.dumps({"response": i}),
                **{"Content-Type": "application/json"})

        for i in methods:
            data = await self._request(i.upper(), f"/{i}", data={"request": i})
            data.json.should.equal({"response": i})
            assert bytes(i, encoding="utf-8") in httpretty.last_request.body
        httpretty.latest_requests.should.have.length_of(4)
