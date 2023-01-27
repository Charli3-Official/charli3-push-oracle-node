""" Business logic for calculating the aggregation and consensus."""
from typing import List
import random


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
