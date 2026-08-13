"""Tests for list_utils: chunk, flatten, dedupe."""

import pytest

import list_utils
from list_utils import chunk, flatten, dedupe


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

def test_functions_exported_at_package_level():
    assert list_utils.chunk is chunk
    assert list_utils.flatten is flatten
    assert list_utils.dedupe is dedupe


# ---------------------------------------------------------------------------
# chunk
# ---------------------------------------------------------------------------

class TestChunk:
    def test_basic_uneven(self):
        assert chunk([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]

    def test_empty_list(self):
        assert chunk([], 3) == []

    def test_size_larger_than_list(self):
        assert chunk([1, 2, 3], 10) == [[1, 2, 3]]

    def test_exact_division(self):
        assert chunk([1, 2, 3, 4], 2) == [[1, 2], [3, 4]]

    def test_uneven_division(self):
        assert chunk([1, 2, 3, 4, 5], 3) == [[1, 2, 3], [4, 5]]

    def test_size_one(self):
        assert chunk([1, 2, 3], 1) == [[1], [2], [3]]

    def test_single_element(self):
        assert chunk([42], 5) == [[42]]

    def test_preserves_item_types(self):
        assert chunk(["a", "b", "c"], 2) == [["a", "b"], ["c"]]

    def test_accepts_any_iterable(self):
        # chunk should work on any iterable, not just lists
        assert chunk((1, 2, 3, 4), 2) == [[1, 2], [3, 4]]

    def test_size_zero_raises_value_error(self):
        with pytest.raises(ValueError):
            chunk([1, 2, 3], 0)

    def test_size_negative_raises_value_error(self):
        with pytest.raises(ValueError):
            chunk([1, 2, 3], -1)

    def test_size_non_int_raises_value_error(self):
        with pytest.raises(ValueError):
            chunk([1, 2, 3], 2.5)

    def test_size_bool_raises_value_error(self):
        # bool is a subclass of int but not a valid size
        with pytest.raises(ValueError):
            chunk([1, 2, 3], True)

    def test_value_error_message_mentions_positive(self):
        with pytest.raises(ValueError, match="positive"):
            chunk([1, 2, 3], 0)


# ---------------------------------------------------------------------------
# flatten
# ---------------------------------------------------------------------------

class TestFlatten:
    def test_deeply_nested(self):
        assert flatten([1, [2, [3, [4]]]]) == [1, 2, 3, 4]

    def test_strings_are_atomic(self):
        assert flatten(["ab", ["cd"]]) == ["ab", "cd"]

    def test_already_flat(self):
        assert flatten([1, 2, 3]) == [1, 2, 3]

    def test_empty_list(self):
        assert flatten([]) == []

    def test_nested_empty_lists(self):
        assert flatten([[], [[]], [[], []]]) == []

    def test_empty_string_is_atomic(self):
        # Empty string must not be iterated char-by-char (which would yield
        # nothing) — it should appear as an atomic element.
        assert flatten(["", ["a"]]) == ["", "a"]

    def test_mixed_types(self):
        assert flatten([1, ["a", [None, [2]]]]) == [1, "a", None, 2]

    def test_tuples_are_iterated(self):
        assert flatten([(1, 2), [3]]) == [1, 2, 3]

    def test_nested_tuple(self):
        assert flatten([1, (2, (3,))]) == [1, 2, 3]

    def test_non_iterable_passed_directly(self):
        # flatten iterates over its argument, so a bare int is not valid;
        # but a list containing non-iterables works.
        assert flatten([42, [13]]) == [42, 13]

    def test_very_deep_nesting(self):
        nested = 1
        for _ in range(100):
            nested = [nested]
        assert flatten(nested) == [1]

    def test_strings_with_nested_strings(self):
        assert flatten(["hello", ["world", ["!"]]]) == ["hello", "world", "!"]

    def test_preserves_none(self):
        assert flatten([None, [None, [None]]]) == [None, None, None]


# ---------------------------------------------------------------------------
# dedupe
# ---------------------------------------------------------------------------

class TestDedupe:
    def test_basic(self):
        assert dedupe([1, 2, 2, 3, 1]) == [1, 2, 3]

    def test_no_duplicates(self):
        assert dedupe([1, 2, 3]) == [1, 2, 3]

    def test_all_duplicates(self):
        assert dedupe([7, 7, 7, 7]) == [7]

    def test_empty_list(self):
        assert dedupe([]) == []

    def test_single_element(self):
        assert dedupe([42]) == [42]

    def test_preserves_order_hashable(self):
        assert dedupe([3, 1, 2, 1, 3, 2]) == [3, 1, 2]

    def test_unhashable_items_fallback(self):
        # list of lists — unhashable, must use the fallback path
        items = [[1, 2], [3], [1, 2], [3], [4]]
        assert dedupe(items) == [[1, 2], [3], [4]]

    def test_unhashable_preserves_order(self):
        items = [[3], [1], [3], [2], [1]]
        assert dedupe(items) == [[3], [1], [2]]

    def test_mixed_hashable_and_unhashable(self):
        # Once an unhashable item triggers TypeError, the whole run restarts
        # on the fallback path. Order must still be preserved.
        items = [1, [2], 1, [2], 3]
        assert dedupe(items) == [1, [2], 3]

    def test_dicts_unhashable(self):
        d1 = {"a": 1}
        d2 = {"b": 2}
        assert dedupe([d1, d2, d1]) == [d1, d2]

    def test_strings(self):
        assert dedupe(["a", "b", "a", "c", "b"]) == ["a", "b", "c"]

    def test_mixed_types_hashable(self):
        assert dedupe([1, "a", 1, "a", None, None]) == [1, "a", None]

    def test_accepts_any_iterable(self):
        assert dedupe((1, 2, 2, 3)) == [1, 2, 3]
