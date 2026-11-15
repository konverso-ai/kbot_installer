"""Literal-value implementation of the secret vault."""

from __future__ import annotations

from typing_extensions import override

from security.vault.base import VaultBase


class ValueVault(VaultBase):
    """``VaultBase`` implementation returning the key itself as the value.

    Settings references embedded in the key are expanded by the settings reader
    before the key reaches the vault.
    """

    @override
    def get(self, key: str) -> str:
        """Return the key.

        Args:
            key: Literal value, used as is (no ``<vault-name>::`` prefix).

        Returns:
            The key.

        """
        return key
