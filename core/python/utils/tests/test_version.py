"""Tests for version module."""

from unittest.mock import patch

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


def test_version_to_json_str_empty_returns_empty_string() -> None:
    """Test that an empty version's to_json_str returns an empty string."""
    assert compare("eq", Version.empty().to_json_str(), "")


def test_version_to_json_str_without_source_falls_back_to_to_str() -> None:
    """Test that to_json_str falls back to to_str when there is no source string."""
    bumped = Version("1.2.3").bump_patch()
    assert compare("eq", bumped.to_json_str(), bumped.to_str())


def test_version_init_raises_type_error_when_parse_returns_unexpected_type() -> None:
    """Test that Version raises TypeError when parse() returns an unexpected type."""
    with patch("utils.version.parse", return_value="not-a-packaging-version"):
        with pytest.raises(TypeError, match="Invalid version"):
            Version("1.2.3")


def test_version_parse_returns_same_instance_when_given_version() -> None:
    """Test that Version.parse returns the same instance when given a Version."""
    version = Version("1.2.3")
    assert Version.parse(version) is version


def test_version_parse_returns_empty_when_given_none() -> None:
    """Test that Version.parse returns an empty version when given None."""
    assert compare("eq", Version.parse(None), Version.empty())


def test_version_parse_builds_from_string() -> None:
    """Test that Version.parse builds a Version from a string."""
    assert compare("eq", Version.parse("1.2.3"), Version("1.2.3"))


def test_version_parse_raises_type_error_for_unsupported_type() -> None:
    """Test that Version.parse raises TypeError for an unsupported type."""
    with pytest.raises(TypeError, match="Expected version string or Version"):
        Version.parse(123)  # type: ignore[arg-type]


def test_version_to_str_with_env_appends_dev_suffix() -> None:
    """Test that to_str appends the -dev suffix when with_env is True and env is dev."""
    version = Version("1.2.3", env="dev")
    assert compare("eq", version.to_str(with_env=True), "1.2.0003-dev")


def test_version_to_str_with_env_omits_suffix_when_env_not_dev() -> None:
    """Test that to_str omits the suffix when with_env is True but env is not dev."""
    version = Version("1.2.3", env="")
    assert compare("eq", version.to_str(with_env=True), "1.2.0003")


def test_version_eq_returns_not_implemented_for_other_types() -> None:
    """Test that __eq__ returns NotImplemented when compared to a non-Version."""
    assert Version("1.2.3").__eq__("1.2.3") is NotImplemented


def test_version_lt_returns_not_implemented_for_other_types() -> None:
    """Test that __lt__ returns NotImplemented when compared to a non-Version."""
    assert Version("1.2.3").__lt__("1.2.4") is NotImplemented


def test_version_repr_non_empty() -> None:
    """Test that __repr__ shows major, minor, and patch for a non-empty version."""
    assert compare(
        "eq", repr(Version("1.2.3")), "Version(major=1, minor=2, patch=3)"
    )


def test_version_repr_empty() -> None:
    """Test that __repr__ returns 'Version(empty)' for an empty version."""
    assert compare("eq", repr(Version.empty()), "Version(empty)")


def test_version_str_uses_to_str() -> None:
    """Test that __str__ delegates to to_str."""
    assert compare("eq", str(Version("1.2.3")), Version("1.2.3").to_str())


def test_version_hash_is_consistent_with_equality() -> None:
    """Test that equal versions produce the same hash."""
    assert compare("eq", hash(Version("1.2.3")), hash(Version("1.2.0003")))


def test_version_to_branch_default_format() -> None:
    """Test that to_branch returns the default 'release-{major.minor}' format."""
    version = Version("1.2.3", env="dev")
    assert compare("eq", version.to_branch(), "release-1.2")


def test_version_to_branch_with_patch_and_env() -> None:
    """Test that to_branch includes patch and env suffix when requested."""
    version = Version("1.2.3", env="dev")
    assert compare(
        "eq",
        version.to_branch(with_patch=True, with_env=True),
        "release-1.2.0003-dev",
    )
