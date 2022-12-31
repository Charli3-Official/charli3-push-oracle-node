#!/usr/bin/env python3

import httpretty
import unittest
import sure
import json

from backend.api import Api

class customApi(Api):
    api_url = "http://persodomain.com"

class TestApiMethods(unittest.TestCase):
    @httpretty.activate(allow_net_connect=False)
    def test_httpbin(self):
        methods = ["get", "post", "put"]
        for m in methods:
            httpretty.register_uri(
                getattr(httpretty, m.upper()),
                f"{customApi.api_url}/{m}",
                body=json.dumps({"response": m})
            )

        ca = customApi()
        for m in methods:
            response_get = ca._request(m.upper(), f"/{m}", data={"request": m})
            response_get.json().should.equal({"response": m})
            assert bytes(m, encoding="utf-8") in httpretty.last_request().body
        httpretty.latest_requests().should.have.length_of(3)