"""Main Api abstract class and a response class to keep the information"""
from dataclasses import dataclass

import aiohttp

@dataclass(init=False)
class ApiResponse():
    """Proxy class for library responses. Used to make the _request method
    agnostic to the library it uses."""
    def __init__(self, resp):
        self._resp = resp
        self.status = self._resp.status
        self.json = None
        self.is_ok = self._resp.ok
        self.headers = self._resp.headers

    async def get_info(self):
        """Load async information from the response object`"""
        self.json = await self._resp.json()

class Api():
    """Abstract class to make an agnostic implementation of http requests"""
    api_url = None
    _header = {
        "Content-type": "application/json",
        "Accepts": "application/json"
    }

    async def _request(self, method, path, data=None, headers=None):
        if headers is None:
            headers = {}
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
