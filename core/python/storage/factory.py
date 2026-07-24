"""Factory functions for creating bucket storage instances."""

from typing import TYPE_CHECKING, cast

from backend.factory import add_backend
from credentials.azure_credentials import AzureCredentials
from credentials.oci_credentials import OciCredentials
from credentials.s3_credentials import S3Credentials
from storage.base import StorageBase
from utils.factory import factory_function
from utils.factory.loader import factory_method

if TYPE_CHECKING:
    from collections.abc import Callable


def add_storage(name: str, **kwargs: object) -> StorageBase:
    """Create a bucket storage instance by name.

    Args:
        name: Name of the bucket storage to create (e.g., "s3").
        **kwargs: Additional arguments to pass to the bucket storage constructor.

    Returns:
        An instance of the specified bucket storage.

    """
    return cast("StorageBase", factory_method(name, "storage", **kwargs))


def add_s3_storage(bucket_name: str, cluster_name: str | None = None) -> StorageBase:
    """Create an S3 storage instance using default boto3 credentials.

    Args:
        bucket_name: S3 bucket name.
        cluster_name: Optional root directory prefix inside the bucket.

    Returns:
        A ready-to-use S3 storage instance.

    """
    credentials = S3Credentials()
    backend = add_backend(name="s3_storage", credentials=credentials)
    return add_storage(
        name="s3",
        backend=backend,
        bucket_name=bucket_name,
        cluster_name=cluster_name,
    )


def add_azure_storage(container_name: str) -> StorageBase:
    """Create an Azure Blob Storage instance using the default Azure credential chain.

    Args:
        container_name: Blob container name.

    Returns:
        A ready-to-use Azure storage instance.

    """
    credentials = AzureCredentials()
    backend = add_backend(name="azure_blob", credentials=credentials)
    return add_storage(name="azure", backend=backend, container_name=container_name)


def add_oci_storage(bucket_name: str, namespace_name: str) -> StorageBase:
    """Create an OCI Object Storage instance using the default OCI config file.

    Args:
        bucket_name: OCI Object Storage bucket name.
        namespace_name: Object Storage namespace of the tenancy.

    Returns:
        A ready-to-use OCI storage instance.

    """
    credentials = OciCredentials()
    backend = add_backend(name="oci_storage", credentials=credentials)
    return add_storage(
        name="oci",
        backend=backend,
        bucket_name=bucket_name,
        namespace_name=namespace_name,
    )


def add_builtin_storage(name: str, **kwargs: object) -> StorageBase:
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
        "Callable[..., StorageBase]",
        factory_function(
            module_name=__name__,
            attribute_name=f"add_{name}_storage",
        ),
    )
    return builder(**kwargs)
