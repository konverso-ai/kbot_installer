"""Factory functions for creating vault instances."""

from typing import TYPE_CHECKING, cast

from backend.base import BackendBase
from security.vault.base import VaultBase
from utils.factory import factory_function
from utils.factory.loader import factory_method

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
    return cast("VaultBase", factory_method(name, "security.vault", **kwargs))


def add_s3_vault(region_name: str | None = None) -> VaultBase:
    """Create an S3 vault instance using default boto3 credentials.

    Args:
        region_name: AWS region of the Secrets Manager. If None,
            ``AWS_DEFAULT_REGION`` (or its default) is used.

    Returns:
        A ready-to-use AWS Secrets Manager vault instance.

    """
    from backend.factory import add_backend  # noqa: PLC0415
    from credentials.s3_credentials import S3Credentials  # noqa: PLC0415

    credentials = S3Credentials(AWS_DEFAULT_REGION=region_name) if region_name else S3Credentials()
    backend = add_backend(name="s3_vault", credentials=credentials)
    return add_vault(name="s3", backend=backend)


def add_azure_vault() -> VaultBase:
    """Create an Azure vault instance using the default Azure credential chain.

    The returned vault serves every Key Vault named in its keys, building one
    backend per Key Vault on first use.

    Returns:
        A ready-to-use Azure Key Vault vault instance.

    """
    from backend.factory import add_backend  # noqa: PLC0415
    from credentials.azure_credentials import AzureCredentials  # noqa: PLC0415

    credentials = AzureCredentials()

    def build_backend(vault_name: str) -> BackendBase:
        return add_backend(name="azure_vault", credentials=credentials, vault_name=vault_name)

    return add_vault(name="azure", backend_factory=build_backend)


def add_oci_vault(
    resolve_secret_id: "Callable[[str], str | None] | None" = None,
) -> VaultBase:
    """Create an OCI vault instance using instance principal authentication.

    Args:
        resolve_secret_id: Function mapping a secret alias to its OCID (see
            ``OciVault``). If None, only secret OCIDs are accepted.

    Returns:
        A ready-to-use OCI Vault vault instance.

    """
    from backend.factory import add_backend  # noqa: PLC0415

    backend = add_backend(name="oci_vault")
    return add_vault(name="oci", backend=backend, resolve_secret_id=resolve_secret_id)


def add_hashicorp_vault() -> VaultBase:
    """Create a HashiCorp vault instance using the ``VAULT_ADDR`` and ``VAULT_TOKEN`` environment variables.

    Returns:
        A ready-to-use HashiCorp Vault vault instance.

    Raises:
        RuntimeError: If ``VAULT_ADDR`` or ``VAULT_TOKEN`` is not set.

    """
    from backend.factory import add_backend  # noqa: PLC0415
    from credentials.hashicorp_credentials import HashicorpCredentials  # noqa: PLC0415

    backend = add_backend(name="hashicorp_vault", credentials=HashicorpCredentials())
    return add_vault(name="hashicorp", backend=backend)


def add_secret_vault(cloud_provider: str, **kwargs: object) -> VaultBase:
    """Create a provider-agnostic secret vault backed by a built-in cloud vault.

    Args:
        cloud_provider: Name of the built-in cloud vault to delegate to
            (e.g. "s3", "azure", "oci").
        **kwargs: Additional arguments forwarded to the matching
            ``add_{cloud_provider}_vault`` helper (e.g. ``region_name`` for "s3").

    Returns:
        A secret vault delegating every lookup to the built-in cloud vault.

    Raises:
        AttributeError: If no ``add_{cloud_provider}_vault`` function exists.

    """
    return add_vault(name="secret", vault=add_builtin_vault(cloud_provider, **kwargs))


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
