"""String utility functions.

This package provides three string utilities:

- :func:`slugify` — produce a URL-safe slug from arbitrary text.
- :func:`truncate` — shorten text to a maximum length with an ellipsis.
- :func:`is_palindrome` — test whether text reads the same forwards and backwards.

All three are exported at the package level, so they can be used as
``string_utils.slugify(...)`` etc.
"""

from __future__ import annotations

import re
import unicodedata

__all__ = ["slugify", "truncate", "is_palindrome"]

# Matches one or more characters that are not ASCII letters or digits.
# Used after accent stripping, so we only care about the ASCII range.
_NON_ALNUM_RUN = re.compile(r"[^a-z0-9]+")
# Matches two or more consecutive hyphens, used to collapse runs.
_MULTI_HYPHEN = re.compile(r"-{2,}")


def slugify(text: str) -> str:
    """Convert ``text`` into a URL-safe slug.

    The transformation proceeds in this order:

    1. Lowercase the text.
    2. Apply NFKD Unicode normalization, which decomposes accented
       characters into their base character plus combining marks.
    3. Strip every combining mark (Unicode category starting with ``M``).
    4. Replace every run of non-alphanumeric characters with a single
       hyphen.
    5. Collapse consecutive hyphens into one.
    6. Trim leading and trailing hyphens.

    Examples:
        >>> slugify("Hello World!")
        'hello-world'
        >>> slugify("café")
        'cafe'
        >>> slugify("")
        ''
    """
    text = text.lower()
    text = unicodedata.normalize("NFKD", text)
    # Drop combining marks (accents) left over from the decomposition.
    text = "".join(
        ch for ch in text if not unicodedata.category(ch).startswith("M")
    )
    # Replace runs of non-alphanumeric characters with a single hyphen.
    text = _NON_ALNUM_RUN.sub("-", text)
    # Collapse any consecutive hyphens that resulted.
    text = _MULTI_HYPHEN.sub("-", text)
    # Trim leading and trailing hyphens.
    return text.strip("-")


def truncate(text: str, length: int) -> str:
    """Truncate ``text`` to at most ``length`` characters.

    - If ``length < 3``, the ellipsis ``"..."`` itself is truncated to
      ``length`` characters and returned (so ``length == 0`` yields the
      empty string).
    - Otherwise, if ``len(text) <= length``, ``text`` is returned
      unchanged.
    - Otherwise, the result is ``text[:length-3] + "..."``, which is
      exactly ``length`` characters long.

    Examples:
        >>> truncate("hello world", 8)
        'hello...'
        >>> truncate("short", 10)
        'short'
        >>> truncate("hello world", 2)
        '..'
    """
    if length < 3:
        return "..."[:length]
    if len(text) <= length:
        return text
    return text[: length - 3] + "..."


def is_palindrome(text: str) -> bool:
    """Return ``True`` if ``text`` is a palindrome.

    All non-alphanumeric characters are stripped and the remaining
    characters are lowercased before the comparison, so phrases such as
    ``"A man, a plan, a canal: Panama"`` count as palindromes. The empty
    string and any single character are considered palindromes.

    Examples:
        >>> is_palindrome("Racecar")
        True
        >>> is_palindrome("A man, a plan, a canal: Panama")
        True
        >>> is_palindrome("hello")
        False
    """
    cleaned = "".join(ch for ch in text if ch.isalnum()).lower()
    return cleaned == cleaned[::-1]
