"""HashiCorp Vault authentication and client management."""

from __future__ import annotations

from typing import TYPE_CHECKING

import hvac

if TYPE_CHECKING:
    from credentials.hashicorp_credentials import HashicorpCredentials


class HashicorpVaultBackend:
    """Backend for HashiCorp Vault secrets."""

    __client: hvac.Client

    def __init__(self, credentials: HashicorpCredentials) -> None:
        """Build the HashiCorp Vault client from the given credentials.

        Args:
            credentials: Vault server address and token.

        Raises:
            RuntimeError: If the address or the token is missing.

        """
        missing = credentials.missing_env_vars()
        if missing:
            msg = f"HashiCorp Vault environment variables are not set: {', '.join(missing)}"
            raise RuntimeError(msg)
        self.__client = hvac.Client(url=credentials.url, token=credentials.token)

    def get_client(self) -> hvac.Client:
        """Return the HashiCorp Vault client."""
        return self.__client
