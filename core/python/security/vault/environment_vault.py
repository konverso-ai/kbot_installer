"""Environment-variable implementation of the secret vault."""

from __future__ import annotations

import os

from typing_extensions import override

from security.vault.base import VaultBase


class EnvironmentVault(VaultBase):
    """``VaultBase`` implementation reading secrets from environment variables."""

    @override
    def get(self, key: str) -> str:
        """Retrieve a secret value from the process environment.

        Args:
            key: Name of the environment variable, used as is (no
                ``<vault-name>::`` prefix).

        Returns:
            The environment variable value.

        Raises:
            RuntimeError: If the environment variable is not defined.

        """
        try:
            return os.environ[key]
        except KeyError:
            msg = f"Environment variable '{key}' is not defined."
            raise RuntimeError(msg) from None
