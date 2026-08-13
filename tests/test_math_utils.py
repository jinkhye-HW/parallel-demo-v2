"""Tests for the math_utils package.

Covers gcd, lcm, is_prime, mean, and median across the documented behavior and
edge cases: negatives, zero, non-int / bool rejection for is_prime, and empty
input handling for mean / median.
"""

import math
import statistics

import pytest

from math_utils import gcd, is_prime, lcm, mean, median


# ---------------------------------------------------------------------------
# Package-level exports
# ---------------------------------------------------------------------------


def test_all_functions_exported_at_package_level():
    import math_utils

    for name in ("gcd", "lcm", "is_prime", "mean", "median"):
        assert hasattr(math_utils, name), f"math_utils missing {name}"


def test_all_functions_have_docstrings():
    for func in (gcd, lcm, is_prime, mean, median):
        assert func.__doc__ is not None and func.__doc__.strip(), (
            f"{func.__name__} should have a non-empty docstring"
        )


# ---------------------------------------------------------------------------
# gcd
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "a,b,expected",
    [
        (12, 8, 4),
        (54, 24, 6),
        (17, 5, 1),  # coprime
        (100, 10, 10),
        (7, 7, 7),
        (0, 5, 5),
        (5, 0, 5),
        (0, 0, 0),
        # negatives -- math.gcd returns a non-negative result.
        (-12, 8, 4),
        (12, -8, 4),
        (-12, -8, 4),
        (-54, -24, 6),
        (-7, 7, 7),
    ],
)
def test_gcd(a, b, expected):
    assert gcd(a, b) == expected


def test_gcd_matches_math_gcd():
    # Spot-check that gcd delegates to math.gcd over a range.
    for a in range(-20, 21):
        for b in range(-20, 21):
            assert gcd(a, b) == math.gcd(a, b)


# ---------------------------------------------------------------------------
# lcm
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "a,b,expected",
    [
        (4, 6, 12),
        (21, 6, 42),
        (5, 7, 35),  # coprime
        (4, 4, 4),
        (1, 5, 5),
        (0, 5, 0),
        (5, 0, 0),
        (0, 0, 0),
        # negatives -- lcm is non-negative.
        (-4, 6, 12),
        (4, -6, 12),
        (-4, -6, 12),
        (-21, -6, 42),
    ],
)
def test_lcm(a, b, expected):
    assert lcm(a, b) == expected


def test_lcm_is_non_negative():
    for a in range(-15, 16):
        for b in range(-15, 16):
            assert lcm(a, b) >= 0


def test_lcm_zero_zero_is_zero():
    assert lcm(0, 0) == 0


# ---------------------------------------------------------------------------
# is_prime
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "n,expected",
    [
        (0, False),
        (1, False),
        (2, True),
        (3, True),
        (4, False),
        (5, True),
        (6, False),
        (7, True),
        (8, False),
        (9, False),
        (10, False),
        (11, True),
        (13, True),
        (15, False),
        (25, False),  # 5 * 5
        (29, True),
        (49, False),  # 7 * 7
        (97, True),  # large prime
        (7919, True),  # larger prime (1000th prime)
        (8009, True),  # also prime
        (8081, True),  # also prime
        (9999, False),  # 9999 = 9 * 1111 = 3 * 3 * 11 * 101
        # negatives
        (-1, False),
        (-2, False),
        (-7, False),
        (-97, False),
    ],
)
def test_is_prime(n, expected):
    assert is_prime(n) is expected


def test_is_prime_large_prime():
    # 104729 is the 10000th prime.
    assert is_prime(104729) is True


def test_is_prime_large_composite():
    # 104730 = 2 * 52365, clearly composite.
    assert is_prime(104730) is False


def test_is_prime_rejects_float():
    with pytest.raises(TypeError):
        is_prime(2.0)


def test_is_prime_rejects_string():
    with pytest.raises(TypeError):
        is_prime("7")


def test_is_prime_rejects_bool_true():
    with pytest.raises(TypeError):
        is_prime(True)


def test_is_prime_rejects_bool_false():
    with pytest.raises(TypeError):
        is_prime(False)


def test_is_prime_rejects_none():
    with pytest.raises(TypeError):
        is_prime(None)


# ---------------------------------------------------------------------------
# mean
# ---------------------------------------------------------------------------


def test_mean_of_list():
    assert mean([1, 2, 3, 4]) == 2.5


def test_mean_of_tuple():
    assert mean((10, 20, 30)) == 20


def test_mean_of_generator():
    gen = (x for x in range(1, 5))  # 1, 2, 3, 4
    assert mean(gen) == 2.5


def test_mean_single_element():
    assert mean([42]) == 42


def test_mean_floats():
    assert mean([1.5, 2.5, 3.0]) == pytest.approx(2.333333, rel=1e-6)


def test_mean_matches_statistics_mean():
    data = [3, 1, 4, 1, 5, 9, 2, 6]
    assert mean(data) == statistics.mean(data)


def test_mean_empty_raises_value_error():
    with pytest.raises(ValueError):
        mean([])


def test_mean_empty_generator_raises_value_error():
    with pytest.raises(ValueError):
        mean(x for x in [])


# ---------------------------------------------------------------------------
# median
# ---------------------------------------------------------------------------


def test_median_odd_count():
    # Middle of [1, 3, 5] is 3.
    assert median([1, 3, 5]) == 3


def test_median_even_count_averages_two_middle():
    # Sorted [1, 3, 5, 7] -> (3 + 5) / 2 == 4.
    assert median([1, 3, 5, 7]) == 4


def test_median_even_count_float_result():
    # Sorted [1, 2, 3, 4] -> (2 + 3) / 2 == 2.5.
    assert median([1, 2, 3, 4]) == 2.5


def test_median_single_element():
    assert median([99]) == 99


def test_median_unsorted_input():
    # median should not require sorted input.
    assert median([5, 1, 3]) == 3
    assert median([7, 1, 5, 3]) == 4


def test_median_of_tuple():
    assert median((4, 1, 3, 2)) == 2.5


def test_median_of_generator():
    gen = (x for x in [10, 2, 8, 4])  # sorted -> [2, 4, 8, 10] -> 6.0
    assert median(gen) == 6.0


def test_median_matches_statistics_median():
    data = [3, 1, 4, 1, 5, 9, 2, 6]
    assert median(data) == statistics.median(data)


def test_median_empty_raises_value_error():
    with pytest.raises(ValueError):
        median([])


def test_median_empty_generator_raises_value_error():
    with pytest.raises(ValueError):
        median(x for x in [])
