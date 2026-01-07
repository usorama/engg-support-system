"""
Utility functions for sample repo fixture.
"""
from typing import List, Any


def helper_function(value: Any) -> str:
    """
    Convert value to string.

    Args:
        value: Any value to convert

    Returns:
        String representation
    """
    return str(value)


def calculate_sum(numbers: List[int]) -> int:
    """
    Calculate sum of numbers.

    Args:
        numbers: List of integers

    Returns:
        Sum of all numbers
    """
    return sum(numbers)


def format_output(data: dict) -> str:
    """
    Format data for output.

    Args:
        data: Dictionary to format

    Returns:
        Formatted string
    """
    lines = [f"{k}: {v}" for k, v in data.items()]
    return "\n".join(lines)
