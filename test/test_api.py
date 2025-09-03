"""Abstract api class testing file"""

import json

import pytest
import sure  # pylint: disable=unused-import
from aioresponses import aioresponses
from charli3_offchain_core.backend import Api


@pytest.mark.asyncio
class TestApiMethods(Api):
    """Test class for all the required http methods"""

    api_url = "http://persodomain.com"

    async def test_httpbin(self):
        """Test that the values returned are correct"""
        methods = ["get", "post", "put", "delete"]
        data = None
        with aioresponses() as m:
            for i in methods:
                getattr(m, i)(
                    f"{self.api_url}/{i}",
                    body=json.dumps({"response": i}),
                    content_type="application/json",
                )

            for i in methods:
                if i.upper() == "GET":
                    data = await self._get(f"/{i}", data={"request": i})
                if i.upper() == "POST":
                    data = await self._post(f"/{i}", data={"request": i})
                if i.upper() == "PUT":
                    data = await self._put(f"/{i}", data={"request": i})
                if i.upper() == "DELETE":
                    data = await self._delete(f"/{i}", data={"request": i})
                data.json.should.equal({"response": i})  # type: ignore[union-attr]
