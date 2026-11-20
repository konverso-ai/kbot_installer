"""Azure Key Vault implementation of the secret vault."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from typing_extensions import override

from utils.Logger import logger
from vault.base import VaultBase

if TYPE_CHECKING:
    from azure.keyvault.secrets import SecretClient

    from backend.base import BackendBase

log = logger.get_package_logger("vault")


class AzureVault(VaultBase):
    """``VaultBase`` implementation backed by Azure Key Vault."""

    _backend: BackendBase

    def __init__(self, backend: BackendBase) -> None:
        """Initialize the Azure vault.

        Args:
            backend: Pre-configured Azure Key Vault backend used to reach
                Azure Key Vault. Building the backend (and its credentials,
                including the target vault name) is not this class's
                responsibility.

        """
        self._backend = backend

    def _get_client(self) -> SecretClient | None:
        """Return the Azure Key Vault client from the configured backend."""
        return cast("SecretClient | None", self._backend.get_client())

    @override
    def get(self, key: str) -> str:
        """Retrieve a secret value from Azure Key Vault.

        Args:
            key: Secret key in the ``<vault-name>::<key-in-vault>`` form. The
                backend's client is already bound to a specific vault (via its
                vault URL, built from the vault name at backend construction
                time), so the vault name segment is not used here;
                ``key-in-vault`` is used as the secret name.

        Returns:
            The secret value.

        Raises:
            ValueError: If ``key`` is not in the ``<vault-name>::<key-in-vault>`` form.
            RuntimeError: If the Azure Key Vault client is unavailable, or if the
                retrieved secret has no value.

        """
        _, secret_name = self.parse_key(key)
        client = self._get_client()
        if client is None:
            msg = (
                "Azure Key Vault client unavailable. Ensure the Azure backend "
                "is configured."
            )
            raise RuntimeError(msg)

        value = client.get_secret(secret_name).value
        if value is None:
            msg = f"Secret '{secret_name}' has no value in Azure Key Vault."
            raise RuntimeError(msg)
        return value
