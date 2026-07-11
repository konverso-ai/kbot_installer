"""Normalize scalar or list values into lists."""

from typing import Any


def as_list(value: Any) -> list[Any]:
    """Normalize a scalar or list value into a list.

    Args:
        value: Input value that may be absent, a single item, or a list.

    Returns:
        Empty list when value is falsy; otherwise a list of items.

    """
    if not value:
        return []
    return value if isinstance(value, list) else [value]
