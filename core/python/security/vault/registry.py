"""Registry of the kbot vaults usable in ``<VAULT>::<key>`` setting values."""

from __future__ import annotations

from typing import TYPE_CHECKING

from security.vault import factory

if TYPE_CHECKING:
    from collections.abc import Callable

    from security.vault.base import VaultBase

#: kbot vault name -> builder of its ``security.vault`` implementation.
_BUILDERS: dict[str, Callable[..., VaultBase]] = {
    "VARIABLE": lambda **kwargs: factory.add_vault("environment", **kwargs),
    "VALUE": lambda **kwargs: factory.add_vault("value", **kwargs),
    "ALIAS": lambda **kwargs: factory.add_vault("alias", **kwargs),
    "SECRET": lambda **kwargs: factory.add_vault("secret", **kwargs),
    "AZUREKEYVAULT": factory.add_azure_vault,
    "AWSSECRETMANAGER": factory.add_s3_vault,
    "OCIVAULT": factory.add_oci_vault,
}


class VaultRegistry:
    """Registry of the kbot vaults, each registered when it is first requested."""

    def __init__(self) -> None:
        """Start with no vault registered."""
        self._vaults: dict[str, VaultBase] = {}

    def __contains__(self, name: object) -> bool:
        """Tell whether ``name`` is a kbot vault name, without building the vault."""
        return name in _BUILDERS

    def get(self, name: str, **kwargs: object) -> VaultBase:
        """Return the vault registered under ``name``, building and registering it on first call.

        Args:
            name: kbot vault name, e.g. ``VARIABLE`` or ``AZUREKEYVAULT``.
            **kwargs: Arguments of the vault builder (e.g. ``get_config`` for ``ALIAS``,
                ``vault`` for ``SECRET``, ``region_name`` for ``AWSSECRETMANAGER``,
                ``resolve_secret_id`` for ``OCIVAULT``); only used when the vault is built.

        Returns:
            The registered vault.

        Raises:
            KeyError: If ``name`` is not a kbot vault name.

        """
        if name not in self._vaults:
            self._vaults[name] = _BUILDERS[name](**kwargs)
        return self._vaults[name]
