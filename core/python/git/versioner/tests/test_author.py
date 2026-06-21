"""Tests for versioner.author module."""

import pytest

from utils.utils_for_unit_tests import compare
from git.versioner.author import Author


@pytest.mark.parametrize(
    "params, expected",
    [
        (
            {"name": "Git Versioner", "email": "versioner@example.com"},
            "Git Versioner <versioner@example.com>",
        ),
        (
            {"name": "Jane Doe", "email": "jane@example.org"},
            "Jane Doe <jane@example.org>",
        ),
    ],
)
def test_formatted_valid_returns_git_author_string(params: dict, expected: str) -> None:
    author = Author(**params)
    assert compare("eq", author.formatted, expected)
    assert compare("eq", author.to_str(), expected)
    assert compare("eq", author.to_bytes(), expected.encode())
