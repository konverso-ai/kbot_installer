"""Azure Key Vault implementation of the secret vault."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from typing_extensions import override

from security.vault.base import VaultBase
from utils.Logger import logger

if TYPE_CHECKING:
    from collections.abc import Callable

    from azure.keyvault.secrets import SecretClient

    from backend.base import BackendBase

log = logger.get_package_logger("vault")


class AzureVault(VaultBase):
    """``VaultBase`` implementation backed by Azure Key Vault.

    Keys name the target Key Vault (``<vault-name>::<secret-name>``), so one
    instance serves any number of Key Vaults; one backend is built and cached
    per vault name.
    """

    _backend_factory: Callable[[str], BackendBase]
    _backends: dict[str, BackendBase]

    def __init__(self, backend_factory: Callable[[str], BackendBase]) -> None:
        """Initialize the Azure vault.

        Args:
            backend_factory: Function building the pre-configured Azure Key
                Vault backend of a given Key Vault name. Building backends (and
                their credentials) is not this class's responsibility.

        """
        self._backend_factory = backend_factory
        self._backends = {}

    def _get_client(self, vault_name: str) -> SecretClient:
        """Return the client of a Key Vault, building its backend on first use.

        Args:
            vault_name: Name of the Azure Key Vault.

        Returns:
            The Key Vault secret client.

        Raises:
            RuntimeError: If the backend provides no client.

        """
        backend = self._backends.get(vault_name)
        if backend is None:
            backend = self._backends[vault_name] = self._backend_factory(vault_name)
        client = cast("SecretClient | None", backend.get_client())
        if client is None:
            msg = (
                f"Azure Key Vault client unavailable for vault '{vault_name}'. Ensure the Azure backend is configured."
            )
            raise RuntimeError(msg)
        return client

    @override
    def get(self, key: str) -> str:
        """Retrieve a secret value from Azure Key Vault.

        Args:
            key: Secret key in the ``<vault-name>::<secret-name>`` form.

        Returns:
            The secret value.

        Raises:
            ValueError: If ``key`` is not in the ``<vault-name>::<secret-name>`` form.
            RuntimeError: If the Azure Key Vault client is unavailable, or if the
                retrieved secret has no value.

        """
        vault_name, secret_name = self.parse_key(key)
        value = self._get_client(vault_name).get_secret(secret_name).value
        if value is None:
            msg = f"Secret '{secret_name}' has no value in Azure Key Vault '{vault_name}'."
            raise RuntimeError(msg)
        return value

    @override
    def set(self, key: str, value: str) -> None:
        """Create or replace a secret in Azure Key Vault.

        Args:
            key: Secret key in the ``<vault-name>::<secret-name>`` form.
            value: Secret value to store.

        Raises:
            ValueError: If ``key`` is not in the ``<vault-name>::<secret-name>`` form.
            RuntimeError: If the Azure Key Vault client is unavailable.

        """
        vault_name, secret_name = self.parse_key(key)
        self._get_client(vault_name).set_secret(secret_name, value)
