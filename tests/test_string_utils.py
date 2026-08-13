"""Tests for the ``string_utils`` package.

Covers ``slugify``, ``truncate``, and ``is_palindrome`` plus the edge
cases enumerated in ticket #4.
"""

from __future__ import annotations

import string_utils


# ---------------------------------------------------------------------------
# slugify
# ---------------------------------------------------------------------------


class TestSlugify:
    def test_basic_example(self):
        assert string_utils.slugify("Hello World!") == "hello-world"

    def test_strips_accents_nfkd(self):
        # NFKD decomposes é into 'e' + combining acute accent, which is
        # then dropped, leaving plain ASCII 'e'.
        assert string_utils.slugify("café") == "cafe"

    def test_strips_german_umlaut(self):
        # 'ü' decomposes to 'u' + combining diaeresis.
        assert string_utils.slugify("München") == "munchen"

    def test_empty_string(self):
        assert string_utils.slugify("") == ""

    def test_only_special_chars(self):
        assert string_utils.slugify("!!!???") == ""

    def test_collapses_consecutive_separators(self):
        # Multiple spaces and special chars collapse to a single hyphen.
        assert string_utils.slugify("  multiple   spaces  ") == "multiple-spaces"

    def test_collapses_mixed_special_char_runs(self):
        assert string_utils.slugify("a,,,...b") == "a-b"

    def test_trims_leading_and_trailing_hyphens(self):
        assert string_utils.slugify("---leading trailing---") == "leading-trailing"

    def test_numbers_preserved(self):
        assert string_utils.slugify("item 42 price 99") == "item-42-price-99"

    def test_only_numbers(self):
        assert string_utils.slugify("42") == "42"

    def test_preserves_hyphens_already_present(self):
        # Existing hyphens are non-alphanumeric runs and collapse with
        # any surrounding separators.
        assert string_utils.slugify("foo--bar") == "foo-bar"

    def test_mixed_case_and_accents(self):
        assert string_utils.slugify("Café MÜNCHEN!") == "cafe-munchen"


# ---------------------------------------------------------------------------
# truncate
# ---------------------------------------------------------------------------


class TestTruncate:
    def test_truncates_long_text(self):
        # "hello world" is 11 chars; length 8 -> "hello" + "..." = 8 chars.
        assert string_utils.truncate("hello world", 8) == "hello..."

    def test_short_text_unchanged(self):
        assert string_utils.truncate("short", 10) == "short"

    def test_exact_length_unchanged(self):
        # len("abc") == 3 == length, so returned unchanged.
        assert string_utils.truncate("abc", 3) == "abc"

    def test_length_less_than_three(self):
        # length < 3 -> "..."[:length]
        assert string_utils.truncate("hello world", 2) == ".."
        assert string_utils.truncate("hello world", 1) == "."
        assert string_utils.truncate("hello world", 0) == ""

    def test_length_zero(self):
        assert string_utils.truncate("anything", 0) == ""

    def test_empty_text(self):
        assert string_utils.truncate("", 10) == ""
        assert string_utils.truncate("", 0) == ""
        assert string_utils.truncate("", 2) == ".."

    def test_truncated_result_has_exact_length(self):
        text = "a" * 50
        for length in (10, 20, 30):
            result = string_utils.truncate(text, length)
            assert len(result) == length
            assert result.endswith("...")

    def test_truncate_at_boundary(self):
        # length 3 with text longer than 3 -> text[:0] + "..." = "..."
        assert string_utils.truncate("abcdef", 3) == "..."


# ---------------------------------------------------------------------------
# is_palindrome
# ---------------------------------------------------------------------------


class TestIsPalindrome:
    def test_simple_palindrome_mixed_case(self):
        assert string_utils.is_palindrome("Racecar") is True

    def test_classic_phrase_palindrome(self):
        assert (
            string_utils.is_palindrome("A man, a plan, a canal: Panama")
            is True
        )

    def test_non_palindrome(self):
        assert string_utils.is_palindrome("hello") is False

    def test_single_character(self):
        assert string_utils.is_palindrome("a") is True

    def test_empty_string(self):
        assert string_utils.is_palindrome("") is True

    def test_with_punctuation_and_spaces(self):
        assert string_utils.is_palindrome("Was it a car or a cat I saw?") is True

    def test_all_punctuation(self):
        # Strips to empty string, which equals its reverse.
        assert string_utils.is_palindrome(".,!?") is True

    def test_unicode_palindrome(self):
        # 'ß' is alphanumeric; after lowercasing and stripping the space
        # the cleaned text 'süßßüs' is symmetric.
        assert string_utils.is_palindrome("Süß ßüS") is True

    def test_unicode_non_palindrome(self):
        assert string_utils.is_palindrome("München") is False

    def test_numeric_palindrome(self):
        assert string_utils.is_palindrome("12321") is True

    def test_numeric_non_palindrome(self):
        assert string_utils.is_palindrome("12345") is False


# ---------------------------------------------------------------------------
# Package surface
# ---------------------------------------------------------------------------


class TestPackageSurface:
    def test_all_three_functions_exported(self):
        assert set(string_utils.__all__) == {
            "slugify",
            "truncate",
            "is_palindrome",
        }
        for name in string_utils.__all__:
            assert hasattr(string_utils, name)
            assert callable(getattr(string_utils, name))

    def test_functions_have_docstrings(self):
        for name in string_utils.__all__:
            func = getattr(string_utils, name)
            assert func.__doc__, f"{name} is missing a docstring"
