"""Provider-agnostic implementation of the secret vault."""

from __future__ import annotations

from typing import TYPE_CHECKING

from typing_extensions import override

from security.vault.base import VaultBase

if TYPE_CHECKING:
    from collections.abc import Callable


class SecretVault(VaultBase):
    """``VaultBase`` implementation delegating to a cloud-provider vault.

    Lets configuration reference secrets without knowing which cloud-provider
    vault (AWS Secrets Manager, Azure Key Vault, OCI Vault) backs them.
    """

    _vault: VaultBase
    _expand: Callable[[str], str] | None

    def __init__(
        self,
        vault: VaultBase,
        expand: Callable[[str], str] | None = None,
    ) -> None:
        """Initialize the secret vault.

        Args:
            vault: Cloud-provider vault every lookup is delegated to. Building
                it is not this class's responsibility.
            expand: Function expanding settings references embedded in the key
                before delegating (e.g. kbot's ``Settings()._ExpandConfigValue``).
                If None, the key is delegated unchanged.

        """
        self._vault = vault
        self._expand = expand

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
        if self._expand is not None:
            key = self._expand(key)
        return self._vault.get(key)
