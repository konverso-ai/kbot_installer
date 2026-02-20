"""Factory module for creating vault instances."""

from kbot_installer.core.factory import factory_method
from kbot_installer.core.vault.vault_base import VaultBase


def create_vault(vault_type: str, **kwargs: object) -> VaultBase:
    """Create a vault instance by type name.

    This factory function creates vault instances using the generic factory module.
    The vault_type parameter is used to determine which concrete vault class to instantiate.

    Args:
        vault_type (str): The type of vault to create (e.g., 'alias', 'azure', 'environment').
        **kwargs (object): Additional keyword arguments passed to the vault constructor.

    Returns:
        VaultBase: An instance of the requested vault type.

    Raises:
        ImportError: If the vault module cannot be imported.
        AttributeError: If the vault class cannot be found in the module.
        TypeError: If the vault class cannot be instantiated with the provided arguments.

    Example:
        >>> # Create an alias vault
        >>> alias_vault = create_vault("ALIAS")

    """
    # Use the generic factory to create vault instances
    # vault_type is the class name (e.g., "alias" -> AliasVault)
    return factory_method(vault_type, __package__, **kwargs)
