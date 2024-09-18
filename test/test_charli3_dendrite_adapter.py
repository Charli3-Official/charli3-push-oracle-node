import pytest

from backend.api.providers import Charli3DendriteAdapter


@pytest.mark.asyncio
class TestCharli3DendriteAdapterClass:
    """Testing Charli3DendriteAdapter class."""

    @pytest.fixture()
    async def setup_adapter(self) -> Charli3DendriteAdapter:
        """Fixture to initialize the adapter and call get_rates once."""

        return Charli3DendriteAdapter(
            asset_a="b6a7467ea1deb012808ef4e87b5ff371e85f7142d7b356a40d9b42a0436f726e75636f70696173205b76696120436861696e506f72742e696f5d",
            asset_b="lovelace",
            pair_type="base",
            sources=["minswapv2", "spectrum", "muesliswap", "vyfi"],
            quote_required=False,
        )

    async def test_get_rates(self, setup_adapter):
        """Test get_rates method."""

        adapter = await setup_adapter

        data = await adapter.get_rates()

        # Ensure 'data' is a dictionary and contains the expected keys
        assert isinstance(data, dict), "Expected 'data' to be a dictionary"
        assert "asset_a_name" in data, "'asset_a_name' key not found"
        assert "asset_b_name" in data, "'asset_b_name' key not found"
        assert "rates" in data, "'rates' key not found"

        # Validate rates array length and sources
        rates = data["rates"]
        assert len(rates) == 4, f"Expected 4 rates, but got {len(rates)}"
        assert all(
            isinstance(rate, dict) for rate in rates
        ), "Expected all rates to be dictionaries"

    async def test_get_asset_names(self, setup_adapter):
        """Test get_asset_names method."""
        adapter = await setup_adapter
        asset_a_name, asset_b_name = adapter.get_asset_names()

        assert (
            asset_a_name == "Cornucopias [via ChainPort.io]"
        ), "Expected correct asset_a_name"
        assert asset_b_name == "ADA", "Expected correct asset_b_name"

    async def test_get_sources(self, setup_adapter):
        """Test get_sources method."""
        adapter = await setup_adapter
        sources = adapter.get_sources()
        expected_sources = ["minswapv2", "spectrum", "muesliswap", "vyfi"]

        assert (
            sources == expected_sources
        ), f"Expected sources {expected_sources}, but got {sources}"
