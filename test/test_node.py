"""Node contract class testing file"""

import json
from unittest import mock

import pytest
import sure # pylint: disable=unused-import
from mocket import async_mocketize
from mocket.plugins.httpretty import httpretty

@pytest.mark.asyncio
class TestNode():
    """Test class for all the required http methods"""


class AsyncMock(mock.MagicMock):
    """Mock for asyncio.sleep"""
    # pylint: disable=invalid-overridden-method
    # pylint: disable=useless-super-delegation
    async def __call__(self, *args, **kwargs):
        return super().__call__(*args, **kwargs)
