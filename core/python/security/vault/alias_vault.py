"""Settings-alias implementation of the secret vault."""

from __future__ import annotations

from typing import TYPE_CHECKING

from typing_extensions import override

from security.vault.base import VaultBase

if TYPE_CHECKING:
    from collections.abc import Callable


class AliasVault(VaultBase):
    """``VaultBase`` implementation making one setting point to another.

    The key names another setting; the value of that setting is returned.
    """

    _get_config: Callable[[str], str | None]

    def __init__(self, get_config: Callable[[str], str | None]) -> None:
        """Initialize the alias vault.

        Args:
            get_config: Function returning the value of a setting by name, or
                None when the setting is undefined (e.g. kbot's
                ``Settings().GetConfig``).

        """
        self._get_config = get_config

    @override
    def get(self, key: str) -> str:
        """Return the value of the setting the key points to.

        Args:
            key: Name of the target setting, used as is (no
                ``<vault-name>::`` prefix).

        Returns:
            The target setting value.

        Raises:
            RuntimeError: If the target setting is not defined.

        """
        value = self._get_config(key)
        if value is None:
            msg = f"Alias target setting '{key}' is not defined."
            raise RuntimeError(msg)
        return value
