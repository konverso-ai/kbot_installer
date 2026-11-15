"""Settings-alias implementation of the secret vault."""

from __future__ import annotations

from typing import TYPE_CHECKING

from typing_extensions import override

from security.vault.base import VaultBase

if TYPE_CHECKING:
    from collections.abc import Callable


class AliasVault(VaultBase):
    """``VaultBase`` implementation making one setting point to another.

    The key names another setting (possibly built from settings references,
    which are expanded first); the value of that setting is returned.
    """

    _get_config: Callable[[str], str | None]
    _expand: Callable[[str], str]

    def __init__(
        self,
        get_config: Callable[[str], str | None],
        expand: Callable[[str], str],
    ) -> None:
        """Initialize the alias vault.

        Args:
            get_config: Function returning the value of a setting by name, or
                None when the setting is undefined (e.g. kbot's
                ``Settings().GetConfig``).
            expand: Function expanding settings references embedded in a
                value (e.g. kbot's ``Settings()._ExpandConfigValue``).

        """
        self._get_config = get_config
        self._expand = expand

    @override
    def get(self, key: str) -> str:
        """Return the value of the setting the key points to.

        Args:
            key: Name of the target setting, used as is (no
                ``<vault-name>::`` prefix). Embedded settings references are
                expanded before the lookup.

        Returns:
            The target setting value.

        Raises:
            RuntimeError: If the target setting is not defined.

        """
        target = self._expand(key)
        value = self._get_config(target)
        if value is None:
            msg = f"Alias target setting '{target}' is not defined."
            raise RuntimeError(msg)
        return value
