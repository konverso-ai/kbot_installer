"""Provider-agnostic implementation of the secret vault."""

from __future__ import annotations

from typing_extensions import override

from security.vault.base import VaultBase


class SecretVault(VaultBase):
    """``VaultBase`` implementation delegating to a cloud-provider vault.

    Lets configuration reference secrets without knowing which cloud-provider
    vault (AWS Secrets Manager, Azure Key Vault, OCI Vault) backs them.
    """

    _vault: VaultBase

    def __init__(self, vault: VaultBase) -> None:
        """Initialize the secret vault.

        Args:
            vault: Cloud-provider vault every lookup is delegated to. Building
                it is not this class's responsibility.

        """
        self._vault = vault

    @override
    def get(self, key: str) -> str:
        """Retrieve a secret value from the underlying cloud-provider vault.

        Args:
            key: Secret key in the form expected by the underlying vault,
                typically ``<vault-name>::<key-in-vault>``.

        Returns:
            The secret value.

        Raises:
            ValueError: If ``key`` is malformed for the underlying vault.
            RuntimeError: If the underlying vault fails to retrieve the secret.

        """
        return self._vault.get(key)
