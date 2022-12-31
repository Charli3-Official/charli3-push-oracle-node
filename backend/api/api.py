#!/usr/bin/env python3
import requests

class Api(object):
    """Abstract class to make an agnostic implementation of http requests"""
    api_url = None
    _header = {
        "Content-type": "application/json",
        "Accepts": "application/json"
    }

    def _request(self, method, path, data, headers=dict()):
        headers = self._header.update(headers)
        resp = requests.request(
            method=method,
            url=f"{self.api_url}{path}",
            json=data,
            headers=headers
        )
        return resp