"""Math utility functions.

This module provides a small set of number-theoretic and statistical helpers:

- :func:`gcd` -- greatest common divisor of two integers.
- :func:`lcm` -- least common multiple of two integers.
- :func:`is_prime` -- primality test via trial division.
- :func:`mean` -- arithmetic mean of an iterable of values.
- :func:`median` -- median of an iterable of values.

All functions are exported at the package level, so they can be imported
directly, e.g. ``from math_utils import gcd``.
"""

import math
import statistics

__all__ = ["gcd", "lcm", "is_prime", "mean", "median"]


def gcd(a: int, b: int) -> int:
    """Return the greatest common divisor of two integers.

    Delegates to :func:`math.gcd`, which returns a non-negative result and
    handles negative arguments and zero correctly (``gcd(0, 0) == 0``).

    Args:
        a: An integer.
        b: An integer.

    Returns:
        The greatest common divisor of ``a`` and ``b``.
    """
    return math.gcd(a, b)


def lcm(a: int, b: int) -> int:
    """Return the least common multiple of two integers.

    Computed as ``abs(a * b) // gcd(a, b)``. By convention ``lcm(0, 0) == 0``;
    any pair where at least one operand is ``0`` also returns ``0``.

    Args:
        a: An integer.
        b: An integer.

    Returns:
        The least common multiple of ``a`` and ``b``.
    """
    if a == 0 or b == 0:
        return 0
    return abs(a * b) // math.gcd(a, b)


def is_prime(n: int) -> bool:
    """Return ``True`` if ``n`` is a prime number, else ``False``.

    A prime is an integer greater than ``1`` with no positive divisors other
    than ``1`` and itself. This implementation uses trial division up to
    ``sqrt(n)``.

    Args:
        n: An integer to test for primality.

    Returns:
        ``True`` if ``n`` is prime, ``False`` otherwise (including for any
        ``n < 2``).

    Raises:
        TypeError: If ``n`` is not an :class:`int`, or if ``n`` is a
            :class:`bool` (booleans are a subclass of ``int`` but are rejected
            explicitly).
    """
    if not isinstance(n, int) or isinstance(n, bool):
        raise TypeError(
            f"is_prime() requires an int, got {type(n).__name__}"
        )
    if n < 2:
        return False
    if n < 4:
        # 2 and 3 are prime.
        return True
    if n % 2 == 0:
        return False
    # Trial division over odd candidates up to sqrt(n).
    limit = math.isqrt(n)
    for candidate in range(3, limit + 1, 2):
        if n % candidate == 0:
            return False
    return True


def mean(values):
    """Return the arithmetic mean of an iterable of numeric values.

    Accepts any iterable (list, tuple, generator, etc.) and delegates to
    :func:`statistics.mean`. The iterable is materialized into a list first so
    that single-pass generators are supported and so that an empty input raises
    a clear :class:`ValueError` rather than a :class:`statistics.StatisticsError`.

    Args:
        values: An iterable of numeric values.

    Returns:
        The arithmetic mean of ``values``.

    Raises:
        ValueError: If ``values`` is empty.
    """
    materialized = list(values)
    if not materialized:
        raise ValueError("mean() requires at least one data point")
    return statistics.mean(materialized)


def median(values):
    """Return the median of an iterable of numeric values.

    Accepts any iterable (list, tuple, generator, etc.) and delegates to
    :func:`statistics.median`. For an even number of values the two middle
    values are averaged. The iterable is materialized into a list first so
    that single-pass generators are supported and so that an empty input
    raises a clear :class:`ValueError` rather than a
    :class:`statistics.StatisticsError`.

    Args:
        values: An iterable of numeric values.

    Returns:
        The median of ``values`` (the middle value for an odd count, or the
        average of the two middle values for an even count).

    Raises:
        ValueError: If ``values`` is empty.
    """
    materialized = list(values)
    if not materialized:
        raise ValueError("median() requires at least one data point")
    return statistics.median(materialized)
