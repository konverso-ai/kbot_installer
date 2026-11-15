"""Registry of the kbot vaults usable in ``<VAULT>::<key>`` setting values."""

from __future__ import annotations

from typing import TYPE_CHECKING

from security.vault import factory
from utils.Logger import logger

if TYPE_CHECKING:
    from collections.abc import Callable

    from security.vault.base import VaultBase

log = logger.get_package_logger("security.vault")


class VaultRegistry:
    """Registry of the kbot vaults usable in ``<VAULT>::<key>`` setting values.

    Each vault is built on first use, so that a vault whose SDK or settings are
    missing only fails when it is actually used. Lookups never raise: failures are
    logged and reported through the return value, so that kbot's
    ``Settings.GetConfig`` falls back to its own default value.
    """

    def __init__(self, get_config: Callable[[str], str | None], expand: Callable[[str], str]) -> None:
        """Register every vault; none is built until it is first used.

        Args:
            get_config: Function returning the value of a setting by name, or None
                when the setting is undefined (e.g. kbot's ``Settings().GetConfig``).
            expand: Function expanding the ``%(var)v`` settings references embedded in
                a value (e.g. kbot's ``Settings()._ExpandConfigValue``).

        """
        self._builders: dict[str, Callable[[], VaultBase]] = {
            "VARIABLE": lambda: factory.add_vault("environment"),
            "VALUE": lambda: factory.add_vault("value", expand=expand),
            "ALIAS": lambda: factory.add_vault("alias", get_config=get_config, expand=expand),
            # Delegates to the vault named by the ``cloud_provider`` setting (e.g. AZUREKEYVAULT).
            "SECRET": lambda: factory.add_vault(
                "secret", vault=self._get_vault(get_config("cloud_provider") or ""), expand=expand
            ),
            "AZUREKEYVAULT": factory.add_azure_vault,
            "AWSSECRETMANAGER": lambda: factory.add_s3_vault(region_name=get_config("aws_secret_vault_region")),
            "OCIVAULT": lambda: factory.add_oci_vault(resolve_secret_id=get_config),
        }
        self._vaults: dict[str, VaultBase] = {}

    def __contains__(self, name: object) -> bool:
        """Tell whether ``name`` is a known vault name, without building the vault."""
        return name in self._builders

    def get(self, name: str, key: str) -> str | None:
        """Return the value of a key, or a fallback (logged once) when it cannot be resolved.

        Args:
            name: Vault name, e.g. ``VARIABLE`` or ``AZUREKEYVAULT``.
            key: Key in the form expected by the vault (the part after ``<VAULT>::``).

        Returns:
            The resolved value; on failure ``""`` for ``VARIABLE`` (an undefined
            environment variable reads as empty, as kbot always did), None otherwise.

        """
        try:
            return self._get_vault(name).get(key)
        except Exception as e:  # vault failures must not break settings lookups
            # oneTime: the only spelling also provided by kbot's own utils.Logger.
            log.oneTime("warning", "Vault %s could not resolve '%s': %s", name, key, e)
            return "" if name == "VARIABLE" else None

    def set(self, name: str, key: str, value: str) -> bool:
        """Create or replace the value of a key.

        Args:
            name: Vault name, e.g. ``AZUREKEYVAULT``.
            key: Key in the form expected by the vault.
            value: Value to store.

        Returns:
            True on success, False (logged) if the vault is unknown, read-only or
            failed to store the value.

        """
        try:
            self._get_vault(name).set(key, value)
        except Exception:  # reported to the caller through the return value
            log.exception("Vault %s could not store '%s'", name, key)
            return False
        return True

    def _get_vault(self, name: str) -> VaultBase:
        """Return a vault, building it on first use (a failed build is retried on the next call).

        Raises:
            KeyError: If ``name`` is not a known vault name.

        """
        if name not in self._vaults:
            self._vaults[name] = self._builders[name]()
        return self._vaults[name]
