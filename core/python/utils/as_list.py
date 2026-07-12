"""Normalize scalar or list values into lists."""

from typing import TypeVar

T = TypeVar("T")


def as_list(value: T | list[T] | None) -> list[T]:
    """Normalize a scalar or list value into a list.

    Args:
        value: Input value that may be absent, a single item, or a list.

    Returns:
        Empty list when value is falsy; otherwise a list of items.

    """
    if not value:
        return []
    return value if isinstance(value, list) else [value]
