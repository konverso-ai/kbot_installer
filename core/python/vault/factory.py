"""Factory functions for creating vault instances."""

from typing import TYPE_CHECKING, cast

from backend.factory import add_backend
from credentials.azure_credentials import AzureCredentials
from credentials.s3_credentials import S3Credentials
from utils.factory import factory_function
from utils.factory.loader import factory_method
from vault.base import VaultBase

if TYPE_CHECKING:
    from collections.abc import Callable


def add_vault(name: str, **kwargs: object) -> VaultBase:
    """Create a vault instance by name.

    Args:
        name: Name of the vault to create (e.g., "s3").
        **kwargs: Additional arguments to pass to the vault constructor.

    Returns:
        An instance of the specified vault.

    """
    return cast("VaultBase", factory_method(name, "vault", **kwargs))


def add_s3_vault() -> VaultBase:
    """Create an S3 vault instance using default boto3 credentials.

    Returns:
        A ready-to-use AWS Secrets Manager vault instance.

    """
    credentials = S3Credentials()
    backend = add_backend(name="s3_vault", credentials=credentials)
    return add_vault(name="s3", backend=backend)


def add_azure_vault(vault_name: str) -> VaultBase:
    """Create an Azure vault instance using the default Azure credential chain.

    Args:
        vault_name: Name of the Azure Key Vault to connect to.

    Returns:
        A ready-to-use Azure Key Vault vault instance.

    """
    credentials = AzureCredentials()
    backend = add_backend(
        name="azure_vault", credentials=credentials, vault_name=vault_name
    )
    return add_vault(name="azure", backend=backend)


def add_oci_vault() -> VaultBase:
    """Create an OCI vault instance using instance principal authentication.

    Returns:
        A ready-to-use OCI Vault vault instance.

    """
    backend = add_backend(name="oci_vault")
    return add_vault(name="oci", backend=backend)


def add_builtin_vault(name: str, **kwargs: object) -> VaultBase:
    """Create a vault instance using its built-in default-credentials helper.

    Dispatches to the matching helper defined in this module using the naming
    convention ``add_{name}_vault`` (e.g. ``add_s3_vault``, ``add_azure_vault``,
    ``add_oci_vault``).

    Args:
        name: Name of the vault backend to build (e.g. "s3", "azure", "oci").
        **kwargs: Additional arguments forwarded to the matching
            ``add_{name}_vault`` helper.

    Returns:
        A ready-to-use vault instance built with default credentials.

    Raises:
        ImportError: If the current module cannot be imported.
        AttributeError: If no ``add_{name}_vault`` function exists.

    Example:
        >>> vault = add_builtin_vault("s3")

    """
    builder = cast(
        "Callable[..., VaultBase]",
        factory_function(
            module_name=__name__,
            attribute_name=f"add_{name}_vault",
        ),
    )
    return builder(**kwargs)
