"""
Tests for LP Token Adapter

Tests for LP token pricing using on-chain NAV calculation.
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.api.providers.lp_token_adapter import SUPPORTED_LP_DEXES, LPTokenAdapter


@pytest.mark.asyncio
class TestLPTokenAdapter:
    """Test suite for LP Token Adapter"""

    @pytest.fixture
    def mock_pool_state(self):
        """Create a mock pool state object for testing"""
        pool = MagicMock()
        pool.pool_id = "test_pool_id_123"

        # Mock assets (ADA-paired pool with 1M ADA and 1M USDC)
        # For NAV calculation: (1M ADA * 2) / 500K LP = 4 ADA per LP token
        # Formula: (ada_reserve_lovelace * 2) / total_lp_tokens / 1_000_000 = price_in_ADA
        # (1_000_000_000_000 * 2) / 500_000 / 1_000_000 = 4.0 ADA per LP
        pool.assets.model_dump.return_value = {
            "lovelace": 1_000_000_000_000,  # 1M ADA in lovelace
            "usdc_policy_id": 1_000_000_000,  # 1M USDC (6 decimals)
        }

        # Mock LP token with 500K total supply
        # LP tokens are typically whole numbers (no decimals like lovelace)
        pool.lp_token.unit.return_value = "test_lp_token_id"
        pool.lp_token.quantity.return_value = 500_000  # 500K LP tokens

        # Mock for DEXes that use total_liquidity instead
        pool.total_liquidity = 500_000

        return pool

    @pytest.fixture
    def sample_lp_token_id(self):
        """Sample LP token ID for testing"""
        return (
            "b6a7467ea1deb012808ef4e87b5ff371e85f7142d7b356a40d9b42a0"
            + "4c505f544f4b454e"
        )  # "LP_TOKEN" in hex

    def test_adapter_initialization(self, sample_lp_token_id):
        """Test LP token adapter initialization"""
        adapter = LPTokenAdapter(
            lp_token_id=sample_lp_token_id,
            pool_dex="vyfi",
            pair_type="base",
            sources=["vyfi"],
            quote_required=False,
        )

        assert adapter.lp_token_id == sample_lp_token_id
        assert adapter.pool_dex == "vyfi"
        assert adapter.pair_type == "base"
        assert adapter.sources == ["vyfi"]
        assert adapter.quote_required is False

    def test_adapter_initialization_invalid_dex(self, sample_lp_token_id):
        """Test that adapter raises error for unsupported DEX"""
        with pytest.raises(ValueError, match="Unsupported LP DEX"):
            LPTokenAdapter(
                lp_token_id=sample_lp_token_id,
                pool_dex="vyfi",
                pair_type="base",
                sources=["unsupported_dex"],
            )

    def test_get_asset_names(self, sample_lp_token_id):
        """Test asset name extraction from LP token ID"""
        adapter = LPTokenAdapter(
            lp_token_id=sample_lp_token_id,
            pool_dex="vyfi",
            pair_type="base",
        )

        lp_name, ada_name = adapter.get_asset_names()

        assert ada_name == "ADA"
        # LP token name should be decoded from hex
        assert isinstance(lp_name, str)

    def test_calculate_lp_nav_price_vyfi(self, mock_pool_state):
        """Test NAV calculation for VyFi pool with known values"""
        adapter = LPTokenAdapter(
            lp_token_id="test_lp_token_id",
            pool_dex="vyfi",
            pair_type="base",
        )

        # Expected: (1_000_000_000_000 * 2) / 500_000_000_000 / 1_000_000 = 4.0 ADA per LP
        result = adapter._calculate_lp_nav_price(mock_pool_state)

        assert isinstance(result, Decimal)
        assert result == Decimal("4.0")

    def test_calculate_lp_nav_price_minswap(self, mock_pool_state):
        """Test NAV calculation for Minswap pool (uses total_liquidity)"""
        # Remove lp_token.quantity for Minswap-style pool
        delattr(mock_pool_state.lp_token, "quantity")

        adapter = LPTokenAdapter(
            lp_token_id="test_lp_token_id",
            pool_dex="minswapv2",
            pair_type="base",
        )

        result = adapter._calculate_lp_nav_price(mock_pool_state)

        assert isinstance(result, Decimal)
        assert result == Decimal("4.0")

    def test_calculate_lp_nav_price_non_ada_pool(self, mock_pool_state):
        """Test error handling for non-ADA paired pools"""
        # Remove lovelace from pool assets
        mock_pool_state.assets.model_dump.return_value = {
            "usdc_policy": 1_000_000,
            "usdt_policy": 1_000_000,
        }

        adapter = LPTokenAdapter(
            lp_token_id="test_lp_token_id",
            pool_dex="vyfi",
            pair_type="base",
        )

        with pytest.raises(ValueError, match="not ADA-paired"):
            adapter._calculate_lp_nav_price(mock_pool_state)

    def test_calculate_lp_nav_price_invalid_reserve(self, mock_pool_state):
        """Test error handling for invalid ADA reserve"""
        mock_pool_state.assets.model_dump.return_value = {
            "lovelace": 0,  # Invalid: zero reserve
            "usdc_policy": 1_000_000,
        }

        adapter = LPTokenAdapter(
            lp_token_id="test_lp_token_id",
            pool_dex="vyfi",
            pair_type="base",
        )

        with pytest.raises(ValueError, match="Invalid ADA reserve"):
            adapter._calculate_lp_nav_price(mock_pool_state)

    def test_calculate_lp_nav_price_invalid_lp_supply(self, mock_pool_state):
        """Test error handling for invalid LP token supply"""
        mock_pool_state.lp_token.quantity.return_value = 0  # Invalid: zero supply
        mock_pool_state.total_liquidity = 0  # Also set total_liquidity to 0

        adapter = LPTokenAdapter(
            lp_token_id="test_lp_token_id",
            pool_dex="vyfi",
            pair_type="base",
        )

        with pytest.raises(ValueError, match="Invalid LP token supply"):
            adapter._calculate_lp_nav_price(mock_pool_state)

    @patch("backend.api.providers.lp_token_adapter.get_backend")
    async def test_query_pool_by_lp_token_found(
        self, mock_get_backend, mock_pool_state, sample_lp_token_id
    ):
        """Test querying pool by LP token when pool is found"""
        # Setup mock backend
        mock_backend = MagicMock()
        mock_get_backend.return_value = mock_backend

        # Setup mock record
        mock_record = MagicMock()
        mock_record.model_dump.return_value = {
            "datum_hash": "test_hash",
            "datum_cbor": "test_cbor",
        }
        mock_backend.get_pool_utxos.return_value = [mock_record]

        # Setup DEX class mock
        mock_dex_class = MagicMock()
        mock_dex_class.pool_selector.return_value.model_dump.return_value = {
            "addresses": ["test_address"]
        }
        mock_pool_state.lp_token.unit.return_value = sample_lp_token_id
        mock_dex_class.model_validate.return_value = mock_pool_state

        with patch.dict(SUPPORTED_LP_DEXES, {"vyfi": mock_dex_class}):
            adapter = LPTokenAdapter(
                lp_token_id=sample_lp_token_id,
                pool_dex="vyfi",
                pair_type="base",
            )

            result = await adapter._query_pool_by_lp_token("vyfi")

            assert result == mock_pool_state
            mock_backend.get_pool_utxos.assert_called_once()

    @patch("backend.api.providers.lp_token_adapter.get_backend")
    async def test_query_pool_by_lp_token_not_found(
        self, mock_get_backend, sample_lp_token_id
    ):
        """Test querying pool by LP token when pool is not found"""
        mock_backend = MagicMock()
        mock_get_backend.return_value = mock_backend
        mock_backend.get_pool_utxos.return_value = []  # No pools found

        mock_dex_class = MagicMock()
        mock_dex_class.pool_selector.return_value.model_dump.return_value = {
            "addresses": ["test_address"]
        }

        with patch.dict(SUPPORTED_LP_DEXES, {"vyfi": mock_dex_class}):
            adapter = LPTokenAdapter(
                lp_token_id=sample_lp_token_id,
                pool_dex="vyfi",
                pair_type="base",
            )

            result = await adapter._query_pool_by_lp_token("vyfi")

            assert result is None

    @patch("backend.api.providers.lp_token_adapter.get_backend")
    async def test_get_rates_success(
        self, mock_get_backend, mock_pool_state, sample_lp_token_id
    ):
        """Test get_rates returns expected format when pool is found"""
        adapter = LPTokenAdapter(
            lp_token_id=sample_lp_token_id,
            pool_dex="vyfi",
            pair_type="base",
        )

        # Mock the internal methods
        with patch.object(
            adapter, "_query_pool_by_lp_token", return_value=mock_pool_state
        ):
            with patch.object(
                adapter, "_calculate_lp_nav_price", return_value=Decimal("4.0")
            ):
                adapter.set_source_id(
                    "vyfi", "123"
                )  # Pass as string like in actual code

                result = await adapter.get_rates()

                assert result is not None
                assert "asset_a_name" in result
                assert "asset_b_name" in result
                assert result["asset_b_name"] == "ADA"
                assert "rates" in result
                assert len(result["rates"]) == 1
                assert result["rates"][0]["source"] == "vyfi"
                assert result["rates"][0]["price"] == 4.0
                assert result["rates"][0]["source_id"] == "123"

    @patch("backend.api.providers.lp_token_adapter.get_backend")
    async def test_get_rates_no_pool_found(self, mock_get_backend, sample_lp_token_id):
        """Test get_rates returns None when no pool is found"""
        adapter = LPTokenAdapter(
            lp_token_id=sample_lp_token_id,
            pool_dex="vyfi",
            pair_type="base",
        )

        # Mock _query_pool_by_lp_token to return None
        with patch.object(adapter, "_query_pool_by_lp_token", return_value=None):
            result = await adapter.get_rates()

            assert result is None

    def test_get_sources(self, sample_lp_token_id):
        """Test get_sources returns configured sources"""
        adapter = LPTokenAdapter(
            lp_token_id=sample_lp_token_id,
            pool_dex="vyfi",
            pair_type="base",
            sources=["vyfi", "minswapv2"],
        )

        sources = adapter.get_sources()
        assert sources == ["vyfi", "minswapv2"]

    def test_log_sources_summary(self, sample_lp_token_id, caplog):
        """Test logging of adapter configuration summary"""
        adapter = LPTokenAdapter(
            lp_token_id=sample_lp_token_id,
            pool_dex="vyfi",
            pair_type="base",
            sources=["vyfi"],
        )

        adapter._log_sources_summary()

        # Check that logging occurred (logs should mention vyfi and LP token info)
        assert any("vyfi" in record.message for record in caplog.records)

    def test_default_sources(self, sample_lp_token_id):
        """Test that sources defaults to [pool_dex] when not specified"""
        adapter = LPTokenAdapter(
            lp_token_id=sample_lp_token_id,
            pool_dex="vyfi",
            pair_type="base",
        )

        assert adapter.sources == ["vyfi"]

    def test_source_id_management(self, sample_lp_token_id):
        """Test setting and getting source IDs"""
        adapter = LPTokenAdapter(
            lp_token_id=sample_lp_token_id,
            pool_dex="vyfi",
            pair_type="base",
            sources=["vyfi", "minswapv2"],
        )

        adapter.set_source_id("vyfi", "123")  # Pass as string like in actual code
        adapter.set_source_id("minswapv2", "456")

        assert adapter.get_source_id("vyfi") == "123"
        assert adapter.get_source_id("minswapv2") == "456"
        assert adapter.get_source_id("unknown") is None
