"""Smoke tests: each utility package imports as a module."""


def test_math_utils_imports():
    import math_utils

    assert math_utils is not None
    assert hasattr(math_utils, "__name__")
    assert math_utils.__name__ == "math_utils"


def test_string_utils_imports():
    import string_utils

    assert string_utils is not None
    assert hasattr(string_utils, "__name__")
    assert string_utils.__name__ == "string_utils"


def test_list_utils_imports():
    import list_utils

    assert list_utils is not None
    assert hasattr(list_utils, "__name__")
    assert list_utils.__name__ == "list_utils"
