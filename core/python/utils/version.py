"""Semantic version with major, minor, and patch components."""

from functools import total_ordering
from typing import Any, Literal
from typing_extensions import override

from packaging.version import InvalidVersion, Version as PackagingVersion, parse


@total_ordering
class Version:
    """Version parsed from a string using ``packaging``."""

    __slots__ = ("_empty", "_source", "env", "major", "minor", "patch")

    major: int
    minor: int
    patch: int
    env: Literal["dev", ""]
    _empty: bool
    _source: str

    def __init__(self, version: str, env: Literal["dev", ""] = "dev") -> None:
        """Parse *version* into major, minor, and patch components."""
        if not version:
            self._empty = True
            self.major = 0
            self.minor = 0
            self.patch = 0
            self.env = ""
            self._source = ""
            return
        self._empty = False
        self._source = version
        try:
            parsed = parse(version)
        except InvalidVersion as exc:
            raise ValueError(f"Invalid version: {version!r}") from exc
        if not isinstance(parsed, PackagingVersion):
            raise ValueError(f"Invalid version: {version!r}")
        self.major = parsed.major
        self.minor = parsed.minor
        self.patch = parsed.micro
        self.env = env

    @classmethod
    def empty(cls) -> "Version":
        """Return an empty version that serializes to ``""``."""
        return cls("")

    @classmethod
    def parse(cls, value: Any) -> "Version":
        """Build a version from a string, existing instance, or empty value."""
        if isinstance(value, Version):
            return value
        if value is None or value == "":
            return cls.empty()
        if isinstance(value, str):
            return cls(value)
        raise TypeError(
            f"Expected version string or Version, got {type(value).__name__}"
        )

    def to_str(self, with_patch: bool = True, with_env: bool = False) -> str:
        """Return the version as ``major.minor.patch`` with a zero-padded patch."""
        if self._empty:
            return ""
        result = f"{self.major}.{self.minor}"
        if with_patch:
            result += f".{self.patch:04d}"
        if with_env:
            result += f"-{self.env}" if self.env == "dev" else ""
        return result

    def to_json_str(self) -> str:
        """Return the version string for JSON export."""
        if self._empty:
            return ""
        if self._source:
            return self._source
        return self.to_str()

    def bump_patch(self) -> "Version":
        """Return a new version with the patch component incremented."""
        return self._with_parts(patch=self.patch + 1)

    def bump_minor(self) -> "Version":
        """Return a new version with the minor component incremented."""
        return self._with_parts(minor=self.minor + 1, patch=0)

    def bump_major(self) -> "Version":
        """Return a new version with the major component incremented."""
        return self._with_parts(major=self.major + 1, minor=0, patch=0)

    def _with_parts(
        self,
        *,
        major: int | None = None,
        minor: int | None = None,
        patch: int | None = None,
    ) -> "Version":
        new_version = Version.__new__(Version)
        new_version._empty = False
        new_version.major = major if major is not None else self.major
        new_version.minor = minor if minor is not None else self.minor
        new_version.patch = patch if patch is not None else self.patch
        new_version.env = self.env
        new_version._source = ""
        return new_version

    def _key(self) -> tuple[int, int, int]:
        if self._empty:
            return (-1, -1, -1)
        return (self.major, self.minor, self.patch)

    def __bool__(self) -> bool:
        return not self._empty

    @override
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        return self._key() == other._key()

    def __lt__(self, other: "Version") -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        return self._key() < other._key()

    @override
    def __repr__(self) -> str:
        if self._empty:
            return "Version(empty)"
        return f"Version(major={self.major}, minor={self.minor}, patch={self.patch})"

    @override
    def __str__(self) -> str:
        return self.to_str()

    @override
    def __hash__(self) -> int:
        return hash(self._key())

    def to_branch(self, with_patch: bool = False, with_env: bool = False) -> str:
        """Return the version as a branch name."""
        return f"release-{self.to_str(with_patch=with_patch, with_env=with_env)}"
