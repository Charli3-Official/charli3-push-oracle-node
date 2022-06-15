#!/usr/bin/env python3

import aiohttp

class ApiResponse(object):
    """Proxy class for library responses. Used to make the _request method
    agnostic to the library it uses."""
    def __init__(self, resp):
        self._resp = resp

    async def get_info(self):
        self.status = self._resp.status
        self.json = await self._resp.json()
        self.ok = self._resp.ok
        self.headers = self._resp.headers

class Api(object):
    """Abstract class to make an agnostic implementation of http requests"""
    api_url = None
    _header = {
        "Content-type": "application/json",
        "Accepts": "application/json"
    }

    async def _request(self, method, path, data=None, headers=dict()):
        headers = dict(self._header, **headers)
        async with aiohttp.ClientSession() as session:
            async with session.request(
                    method,
                    f"{self.api_url}{path}",
                    json=data,
                    headers=headers) as resp:
                pars = ApiResponse(resp)
                await pars.get_info()
                return pars