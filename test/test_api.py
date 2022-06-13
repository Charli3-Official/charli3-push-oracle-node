#!/usr/bin/env python3

import json

import pytest
import sure
from mocket import async_mocketize
from mocket.plugins.httpretty import httpretty

from backend.api import Api

class customApi(Api):
    api_url = "http://persodomain.com"

@pytest.mark.asyncio
class TestApiMethods():
    @async_mocketize(strict_mode=True)
    async def test_httpbin(self):
        methods = ["get", "post", "put"]
        for m in methods:
            httpretty.register_uri(
                getattr(httpretty, m.upper()),
                f"{customApi.api_url}/{m}",
                body=json.dumps({"response": m}),
                **{"Content-Type": "application/json"})

        ca = customApi()
        for m in methods:
            data = await ca._request(m.upper(), f"/{m}", data={"request": m})
            data.json.should.equal({"response": m})
            assert bytes(m, encoding="utf-8") in httpretty.last_request.body
        httpretty.latest_requests.should.have.length_of(3)