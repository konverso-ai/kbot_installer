"""Tests for version module."""

import pytest

from utils.utils_for_unit_tests import compare
from utils.version import Version


@pytest.mark.parametrize(
    "version, expected",
    [
        ("2024.02.0042", (2024, 2, 42)),
        ("1.2.3", (1, 2, 3)),
        ("2024.02-dev", (2024, 2, 0)),
        ("10.0", (10, 0, 0)),
    ],
)
def test_version_valid_parses_components(
    version: str, expected: tuple[int, int, int]
) -> None:
    parsed = Version(version)
    assert compare("eq", (parsed.major, parsed.minor, parsed.patch), expected)


@pytest.mark.parametrize(
    "version, expected",
    [
        ("2024.02.0042", "2024.2.0042"),
        ("1.2.3", "1.2.0003"),
        ("10.0.1", "10.0.0001"),
    ],
)
def test_version_to_str_valid_formats_patch(version: str, expected: str) -> None:
    assert compare("eq", Version(version).to_str(), expected)


@pytest.mark.parametrize(
    "version, method, expected",
    [
        ("1.2.3", "bump_patch", (1, 2, 4)),
        ("1.2.9999", "bump_patch", (1, 2, 10000)),
        ("1.2.3", "bump_minor", (1, 3, 0)),
        ("1.2.3", "bump_major", (2, 0, 0)),
    ],
)
def test_version_bump_valid_increments_component(
    version: str, method: str, expected: tuple[int, int, int]
) -> None:
    bumped = getattr(Version(version), method)()
    assert compare("eq", (bumped.major, bumped.minor, bumped.patch), expected)


@pytest.mark.parametrize(
    "left, operator, right, expected",
    [
        ("1.2.3", "lt", "1.2.4", True),
        ("1.2.3", "gt", "1.2.4", False),
        ("1.2.3", "eq", "1.2.0003", True),
        ("1.3.0", "gt", "1.2.9999", True),
        ("2.0.0", "ge", "1.9.9999", True),
        ("1.0.0", "le", "1.0.0", True),
    ],
)
def test_version_compare_valid_orders_versions(
    left: str, operator: str, right: str, expected: bool
) -> None:
    assert compare(operator, Version(left), Version(right)) is expected


@pytest.mark.parametrize(
    "version",
    [
        "foo",
        "not-a-version",
    ],
)
def test_version_invalid_raises_value_error(version: str) -> None:
    with pytest.raises(ValueError):
        Version(version)


def test_version_empty_valid_serializes_to_empty_string() -> None:
    assert compare("eq", Version.empty().to_str(), "")
    assert compare("eq", Version.parse(""), Version.empty())
    assert compare("not", Version.empty())


def test_version_to_json_str_preserves_source_format() -> None:
    assert compare("eq", Version("2025.03").to_json_str(), "2025.03")
    assert compare("eq", Version("1.0.0").to_json_str(), "1.0.0")
