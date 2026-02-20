"""Package for secure key-value storage operations.

This package provides a unified interface for vault implementations,
supporting various storage backends like Azure Key Vault, environment variables,
and alias-based storage.
"""

from kbot_installer.core.vault.factory import create_vault
from kbot_installer.core.vault.vault_base import VaultBase

__all__ = [
    "VaultBase",
    "create_vault",
]
