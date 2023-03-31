#!/usr/bin/env python3
"""Chain query class testing."""
import pytest

from backend.core import random_median, aggregation

test_medianrate = [
    ([1, 2, 3, 4, 5], [3]),
    ([1, 2, 3, 4, 10000], [3]),
    ([100, 13, 3, 4, 10000], [13]),
    ([1, 2, 8, 9999, 10000], [8]),
    ([1, 8, 9999, 10000], [8, 9999]),
]

test_aggregation_metrics = [
    (
        (20000, 1500, [2001, 2000, 2002, 1999, 2012]),
        (2001, [2012, 2002, 2001, 2000, 1999], 1999, 2012),
    )
]


class TestConsensus:
    """Tests consensus methods"""

    @pytest.mark.parametrize(
        "rates,medianrate",
        test_medianrate,
    )
    def test_random_median(self, rates, medianrate):
        """for different sets of data gives median"""

        assert random_median(rates) in medianrate

    @pytest.mark.parametrize("inputs,expected", test_aggregation_metrics)
    def test_aggregation(self, inputs, expected):
        """test cases implementation"""

        med, on_consensus, lower, upper = aggregation(*inputs)

        assert med == expected[0]
        assert on_consensus == expected[1]
        assert lower == expected[2]
        assert upper == expected[3]
