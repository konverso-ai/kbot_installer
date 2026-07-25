"""Factory functions for creating backend instances."""

from typing import TYPE_CHECKING, cast

from backend.base import BackendBase
from credentials.azure_credentials import AzureCredentials
from credentials.oci_credentials import OciCredentials
from credentials.s3_credentials import S3Credentials
from utils.factory import factory_function
from utils.factory.loader import factory_method

if TYPE_CHECKING:
    from collections.abc import Callable


def add_backend(name: str, **kwargs: object) -> BackendBase:
    """Create a backend instance by name.

    Args:
        name: Name of the backend to create (e.g., "s3").
        **kwargs: Additional arguments to pass to the backend constructor.

    Returns:
        An instance of the specified backend.

    """
    return cast("BackendBase", factory_method(name, "backend", **kwargs))


def add_s3_storage_backend() -> BackendBase:
    """Create an S3 storage backend using default boto3 credentials.

    Returns:
        A ready-to-use S3 storage backend.

    """
    credentials = S3Credentials()
    return add_backend(name="s3_storage", credentials=credentials)


def add_azure_blob_backend(account_url: str) -> BackendBase:
    """Create an Azure Blob Storage backend using the default Azure credential chain.

    Args:
        account_url: URL of the Azure Storage account to connect to
            (e.g. ``https://{account}.blob.core.windows.net``).

    Returns:
        A ready-to-use Azure Blob Storage backend.

    """
    credentials = AzureCredentials()
    return add_backend(
        name="azure_blob",
        account_url=account_url,
        credentials=credentials,
    )


def add_oci_storage_backend() -> BackendBase:
    """Create an OCI Object Storage backend using the default OCI config file.

    Returns:
        A ready-to-use OCI Object Storage backend.

    """
    credentials = OciCredentials()
    return add_backend(name="oci_storage", credentials=credentials)


def add_builtin_backend(name: str, **kwargs: object) -> BackendBase:
    """Create a storage instance using its built-in default-credentials helper.

    Dispatches to the matching helper defined in this module using the naming
    convention ``add_{name}_storage`` (e.g. ``add_s3_storage``,
    ``add_azure_storage``, ``add_oci_storage``).

    Args:
        name: Name of the storage backend to build (e.g. "s3", "azure", "oci").
        **kwargs: Additional arguments forwarded to the matching
            ``add_{name}_storage`` helper.

    Returns:
        A ready-to-use storage instance built with default credentials.

    Raises:
        ImportError: If the current module cannot be imported.
        AttributeError: If no ``add_{name}_storage`` function exists.

    Example:
        >>> storage = add_builtin_storage("s3", bucket_name="my-bucket")

    """
    builder = cast(
        "Callable[..., BackendBase]",
        factory_function(
            module_name=__name__,
            attribute_name=f"add_{name}_backend",
        ),
    )
    return builder(**kwargs)
