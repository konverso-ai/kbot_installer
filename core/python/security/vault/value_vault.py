"""Literal-value implementation of the secret vault."""

from __future__ import annotations

from typing import TYPE_CHECKING

from typing_extensions import override

from security.vault.base import VaultBase

if TYPE_CHECKING:
    from collections.abc import Callable


class ValueVault(VaultBase):
    """``VaultBase`` implementation returning the key itself as the value.

    The key is a literal value that may embed references to other settings;
    those references are expanded before the value is returned.
    """

    _expand: Callable[[str], str]

    def __init__(self, expand: Callable[[str], str]) -> None:
        """Initialize the value vault.

        Args:
            expand: Function expanding settings references embedded in a
                value (e.g. kbot's ``Settings()._ExpandConfigValue``).

        """
        self._expand = expand

    @override
    def get(self, key: str) -> str:
        """Return the key, with its embedded settings references expanded.

        Args:
            key: Literal value, used as is (no ``<vault-name>::`` prefix).

        Returns:
            The expanded value.

        """
        return self._expand(key)
