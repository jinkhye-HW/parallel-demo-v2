"""List utility functions.

This module provides three order-aware helpers for working with lists:

- :func:`chunk` splits a sequence into fixed-size batches.
- :func:`flatten` fully flattens arbitrarily nested iterables.
- :func:`dedupe` removes duplicates while preserving first-seen order.
"""

from collections.abc import Iterable

__all__ = ["chunk", "flatten", "dedupe"]


def chunk(items, size):
    """Split ``items`` into successive fixed-size batches.

    The last batch may be shorter than ``size`` when the input does not
    divide evenly. An empty input yields an empty list of batches.

    Args:
        items: An iterable to split into chunks.
        size: The maximum length of each batch. Must be a positive integer.

    Returns:
        A list of lists, each of length ``size`` except possibly the last.

    Raises:
        ValueError: If ``size`` is not a positive integer.

    Example:
        >>> chunk([1, 2, 3, 4, 5], 2)
        [[1, 2], [3, 4], [5]]
    """
    if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
        raise ValueError("size must be a positive integer")

    materialized = list(items)
    return [materialized[i : i + size] for i in range(0, len(materialized), size)]


def flatten(nested):
    """Fully flatten an arbitrarily nested iterable.

    Strings (including the empty string) are treated as atomic values and
    are never iterated character by character. Non-iterable items are
    yielded as-is.

    Args:
        nested: An iterable possibly containing other iterables at any depth.

    Returns:
        A flat list of all atomic items in depth-first order.

    Example:
        >>> flatten([1, [2, [3, [4]]]])
        [1, 2, 3, 4]
        >>> flatten(["ab", ["cd"]])
        ['ab', 'cd']
    """
    result = []
    for item in nested:
        if isinstance(item, str) or not isinstance(item, Iterable):
            result.append(item)
        else:
            result.extend(flatten(item))
    return result


def dedupe(items):
    """Remove duplicates from ``items`` while preserving first-seen order.

    Uses a hash-based set for fast membership testing. If an item is
    unhashable (raising ``TypeError``), the function falls back to an
    O(n²) linear scan that compares by equality, still preserving order.

    Args:
        items: An iterable of items to deduplicate.

    Returns:
        A list of items with duplicates removed, in first-seen order.

    Example:
        >>> dedupe([1, 2, 2, 3, 1])
        [1, 2, 3]
    """
    materialized = list(items)
    seen = set()
    result = []
    try:
        for item in materialized:
            if item not in seen:
                seen.add(item)
                result.append(item)
    except TypeError:
        # Fallback for unhashable items: linear scan by equality.
        result = []
        for item in materialized:
            if item not in result:
                result.append(item)
    return result
