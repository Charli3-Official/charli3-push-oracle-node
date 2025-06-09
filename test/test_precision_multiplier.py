"""Test precision multiplier functionality for HOSKY Oracle Feed."""

from math import ceil
from unittest.mock import Mock

import pytest

from backend.runner import FeedUpdater


def test_hosky_precision_calculation():
    """Test HOSKY precision calculations with different multipliers."""
    hosky_rate = 0.00000006691  # Current HOSKY value

    # Old precision (1e6) - causes huge error
    old_precision = 1000000
    old_calculated = ceil(hosky_rate * old_precision)
    old_result = old_calculated / old_precision
    old_error = abs((old_result - hosky_rate) / hosky_rate * 100)

    # New precision (1e12) - much more accurate
    new_precision = 1000000000000
    new_calculated = ceil(hosky_rate * new_precision)
    new_result = new_calculated / new_precision
    new_error = abs((new_result - hosky_rate) / hosky_rate * 100)

    # Assertions
    assert old_error > 1000, f"Old method should have huge error, got {old_error:.2f}%"
    assert (
        new_error < 0.1
    ), f"New method should have minimal error, got {new_error:.6f}%"
    assert old_calculated == 1, f"Old method should ceil to 1, got {old_calculated}"
    assert (
        new_calculated == 66910
    ), f"New method should ceil to 66910, got {new_calculated}"

    # Verify the exact values
    assert old_result == 0.000001, f"Old result should be 0.000001, got {old_result}"
    assert (
        abs(new_result - hosky_rate) < 1e-15
    ), f"New result should be very close to original"


def test_backward_compatibility_standard_feeds():
    """Test that standard feeds (like ADA/USD) remain accurate with 1e6 precision."""
    standard_rates = [0.5, 1.0, 0.25, 0.001, 2.5]  # Typical rates
    precision = 1000000

    for rate in standard_rates:
        calculated = ceil(rate * precision)
        result = calculated / precision
        error = abs((result - rate) / rate * 100)

        # Standard feeds should have very low error with 1e6 precision
        assert error < 0.001, f"Rate {rate} has error {error:.6f}%, should be < 0.001%"


def test_feedupdater_precision_multiplier_parameter():
    """Test that FeedUpdater correctly uses the precision_multiplier parameter."""
    # Mock dependencies
    mock_node = Mock()
    mock_rate = Mock()
    mock_context = Mock()

    # Test with default precision (1e6)
    default_updater = FeedUpdater(
        update_inter=300,
        percent_resolution=100,
        reward_collection_config=None,
        node=mock_node,
        rate=mock_rate,
        context=mock_context,
        precision_multiplier=1000000,
    )

    # Test with HOSKY precision (1e12)
    hosky_updater = FeedUpdater(
        update_inter=300,
        percent_resolution=100,
        reward_collection_config=None,
        node=mock_node,
        rate=mock_rate,
        context=mock_context,
        precision_multiplier=1000000000000,
    )

    # Test the _calculate_rate method
    test_rate = 0.00000006691

    default_result = default_updater._calculate_rate(test_rate)
    hosky_result = hosky_updater._calculate_rate(test_rate)

    assert default_result == 1, f"Default should calculate to 1, got {default_result}"
    assert hosky_result == 66910, f"HOSKY should calculate to 66910, got {hosky_result}"

    # Verify the precision multiplier attribute is set correctly
    assert default_updater.precision_multiplier == 1000000
    assert hosky_updater.precision_multiplier == 1000000000000


def test_precision_multiplier_default_value():
    """Test that FeedUpdater has correct default precision multiplier."""
    # Mock dependencies
    mock_node = Mock()
    mock_rate = Mock()
    mock_context = Mock()

    # Create FeedUpdater without specifying precision_multiplier
    updater = FeedUpdater(
        update_inter=300,
        percent_resolution=100,
        reward_collection_config=None,
        node=mock_node,
        rate=mock_rate,
        context=mock_context,
        # precision_multiplier not specified, should use default
    )

    # Should default to 1e6 for backward compatibility
    assert updater.precision_multiplier == 1000000


def test_calculation_method_change():
    """Test that _calculate_rate is now an instance method using precision_multiplier."""
    # Mock dependencies
    mock_node = Mock()
    mock_rate = Mock()
    mock_context = Mock()

    updater = FeedUpdater(
        update_inter=300,
        percent_resolution=100,
        reward_collection_config=None,
        node=mock_node,
        rate=mock_rate,
        context=mock_context,
        precision_multiplier=123456789,  # Custom precision
    )

    test_rate = 0.001
    expected = ceil(test_rate * 123456789)
    result = updater._calculate_rate(test_rate)

    assert result == expected, f"Expected {expected}, got {result}"

    # Verify it's using the instance precision_multiplier
    assert result == ceil(test_rate * updater.precision_multiplier)


@pytest.mark.parametrize(
    "precision,expected_hosky_result",
    [
        (1000000, 1),  # 1e6 - current default
        (1000000000000, 66910),  # 1e12 - HOSKY precision
        (1000000000, 67),  # 1e9 - intermediate
        (100000000000000, 6691000),  # 1e14 - very high precision
    ],
)
def test_different_precision_multipliers(precision, expected_hosky_result):
    """Test HOSKY calculations with different precision multipliers."""
    hosky_rate = 0.00000006691

    # Mock dependencies
    mock_node = Mock()
    mock_rate = Mock()
    mock_context = Mock()

    updater = FeedUpdater(
        update_inter=300,
        percent_resolution=100,
        reward_collection_config=None,
        node=mock_node,
        rate=mock_rate,
        context=mock_context,
        precision_multiplier=precision,
    )

    result = updater._calculate_rate(hosky_rate)
    assert (
        result == expected_hosky_result
    ), f"With precision {precision}, expected {expected_hosky_result}, got {result}"
