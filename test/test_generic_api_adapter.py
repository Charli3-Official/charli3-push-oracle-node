import pytest

from backend.api.providers import GenericApiAdapter


@pytest.mark.asyncio
class TestGenericApiAdapterClass:
    """Testing GenericApiAdapter class."""

    @pytest.fixture()
    async def setup_adapter(self) -> GenericApiAdapter:
        """Fixture to initialize the adapter and call get_rates once."""

        return GenericApiAdapter(
            asset_a="ADA",
            asset_b="USD",
            sources=[
                {
                    "name": "gate",
                    "api_url": "https://api.gateio.ws/api2/1/ticker/ada_usdt",
                    "json_path": ["last"],
                    "inverse": False,
                }
            ],
            pair_type="base",
            quote_required=False,
        )

    async def test_get_rates(self, setup_adapter):
        """Test get_rates method."""

        adapter = await setup_adapter

        data = await adapter.get_rates()

        # Ensure 'data' is a dictionary and contains the expected keys
        assert isinstance(data, dict), "Expected 'data' to be a dictionary"
        assert "rates" in data, "'rates' key not found"

        # Validate rates array length and sources
        rates = data["rates"]
        assert len(rates) == 1, f"Expected 1 rates, but got {len(rates)}"
        assert all(
            isinstance(rate, dict) for rate in rates
        ), "Expected all rates to be dictionaries"

    async def test_get_asset_names(self, setup_adapter):
        """Test get_asset_names method."""
        adapter = await setup_adapter
        asset_a_name, asset_b_name = adapter.get_asset_names()

        assert asset_a_name == "ADA", "Expected correct asset_a_name"
        assert asset_b_name == "USD", "Expected correct asset_b_name"
