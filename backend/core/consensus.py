""" Business logic for calculating the aggregation and consensus."""
from typing import List, Tuple
from statistics import median
import random

factor_resolution: int = 10000


def random_median(numbers: List[int]):
    """
    This function takes a list of numbers as an input and returns the median of the list.
    The median is calculated as the middle value when the list is sorted.
    When the list has an even number of elements, the median is calculated as a random element
    from the middle two elements.

    Parameters:
    numbers (list): a list of numerical values

    Returns:
    float: median value of the list

    Example:
    median([1, 2, 3, 4, 5, 6]) -> 3 or 4 (randomly)

    """
    numbers.sort()
    if len(numbers) % 2 == 0:
        median1 = numbers[len(numbers) // 2]
        median2 = numbers[len(numbers) // 2 - 1]
        result = random.choice([median1, median2])
    else:
        result = numbers[len(numbers) // 2]
    return result


def aggregation(
    iqrMultiplier: int, diverInPercentage: int, nodeFeeds: List[int]
) -> Tuple[int, List[int], int, int]:
    """
    Calculate the median, onConsensus, lower bound, and upper bound of the aggregated feeds.
    Parameters:
    - iqrMultiplier: k value for outlier detection. The recommended value is 0 (1.5),
      the onchain code has the range restriction between 0 - 4
    - diver: the divergence in percentage (10000)
    - feeds: the feeds to be aggregated
    Returns:
    - A 4-tuple containing the median, onConsensus, lower bound, and upper bound of the
      aggregated feeds.
    """
    sortFeeds = sorted(nodeFeeds)
    _median = int(median(sortFeeds))
    lFeeds = len(sortFeeds)
    onConsensus = consensus(
        sortFeeds, lFeeds, _median, iqrMultiplier, diverInPercentage
    )
    lower = onConsensus[0]
    upper = onConsensus[-1]
    return _median, onConsensus, lower, upper


# The IQR multiplier can be set to any positive value. Small data sets
# with large units as value may be considered as an outlier when it is not,
# here it is convenient to set a higher upper limit.
# It's recommended to use a value of 1.5 for accurate outlier identification.
# This is because, in a standard normal distribution, the quartiles are +/-0.67,
# resulting in an IQR of 1.5. For normally distributed data, the chance of being
# an outlier is about 0.0074, which is less than 1%.
# A value of 3 = ±4.02 standard deviations, about 99.94% of data will fall here
# A value of 4 = ±5.36 standard deviations, about 99.9999% of data will fall here
# http://www.cs.uni.edu/~campbell/stat/normfact.html
# https://en.wikipedia.org/wiki/Probability_density_function
# The scale functions acts as the multiplier by convinience the 0 value
# represents a multiplier of 1.5
def consensus(nodeFeeds, lFeeds, _median, iqrMultiplier, diverInPercentage):
    """
    Calculate the values in the consensus
    Parameters:
    - nodeFeeds: Sorted node feeds list
    - lFeeds:  Length of the nodeFeeds
    - _median: Median value among nodeFeeds
    - iqrMultiplier: k value for outlier detection. The recommended value is 0 (1.5),
      the onchain code has the range restriction between 0 - 4
    - diverInPercentage: Percentage of divergence from the median allowed to
      participate in the consensus
    Returns:
    - A 4-tuple containing the median, onConsensus, lower bound, and upper bound of the
      aggregated feeds.
    """

    # This helper function scales the interquartile range by the given multiplier.
    def scale(t, iqr):
        if t == 0:
            return iqr + iqr // 2
        else:
            return t * iqr

    # This helper function computes how far a given node feed is from the median, in terms of percentage.
    def divergenceFromMedian(nodeFeed):
        return (nodeFeed * factor_resolution) // _median

    # Compute the first and third quartiles of the node feeds.
    firstQuart = firstQuartile(nodeFeeds, lFeeds)
    thirdQuart = thirdQuartile(nodeFeeds, lFeeds)

    # Compute the interquartile range, which is the difference between the third and first quartiles.
    interquartileRange = thirdQuart - firstQuart
    lowerBound = firstQuart - scale(iqrMultiplier, interquartileRange)
    upperBound = thirdQuart + scale(iqrMultiplier, interquartileRange)

    # Finally, we filter out the node feeds that are considered outliers or diverge too much from the median.
    return [
        x
        for x in nodeFeeds
        if divergenceFromMedian(abs(x - _median)) <= diverInPercentage
        and lowerBound <= x <= upperBound
    ]


def firstQuartile(nodeFeeds, lFeeds):
    """
    Calculate the first quartile of the input node feeds
    Parameters:
    - nodeFeeds: Sorted node feeds list
    - lFeeds: Length of the nodeFeeds
    Returns:
    - Node feeds' first quartile
    """
    mid = lFeeds // 2
    return median(nodeFeeds[:mid])


def thirdQuartile(nodeFeeds, lFeeds):
    """
    Calculate the third quartile of the input node feeds
    Parameters:
    - nodeFeeds: Sorted node feeds list
    - lFeeds: Length of the nodeFeeds
    Returns:
    - Node feeds' third quartile
    """
    mid = (lFeeds // 2) + (lFeeds % 2)
    return median(nodeFeeds[mid:])
