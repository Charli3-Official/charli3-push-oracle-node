#!/usr/bin/env python3

from .api import Api

class CoinRate(Api):
    """Abstracts the calls to exchange API's."""
    def __init__(self, api_url, path, json_path, key=None):
        self.api_url = api_url
        self.path = path
        self.json_path = json_path
        self.key = key

    def get_rate(self):
        # TODO: request information and get the value following the json_path
        pass

apis = {
    "binance_adausd": CoinRate(
        "https://api.binance.com",
        "/api/v3/avgPrice?symbol=ADA",
        ["price"]
    )
}