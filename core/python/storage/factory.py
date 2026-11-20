"""Factory functions for creating bucket storage instances."""

from typing import TYPE_CHECKING, cast

from backend.factory import add_builtin_backend
from storage.base import StorageBase
from utils.factory import factory_function
from utils.factory.loader import factory_method

if TYPE_CHECKING:
    from collections.abc import Callable

    import httpx

    from storage.config import StorageSectionConfig


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
    backend = add_builtin_backend(name="s3_storage")
    return add_storage(
        name="s3",
        backend=backend,
        bucket_name=bucket_name,
        cluster_name=cluster_name,
    )


def add_azure_storage(account_url: str, container_name: str) -> StorageBase:
    """Create an Azure Blob Storage instance using the default Azure credential chain.

    Args:
        account_url: URL of the Azure Storage account to connect to
            (e.g. ``https://{account}.blob.core.windows.net``).
        container_name: Blob container name.

    Returns:
        A ready-to-use Azure storage instance.

    """
    backend = add_builtin_backend(name="azure_blob", account_url=account_url)
    return add_storage(name="azure", backend=backend, container_name=container_name)


def add_oci_storage(bucket_name: str, namespace_name: str) -> StorageBase:
    """Create an OCI Object Storage instance using the default OCI config file.

    Args:
        bucket_name: OCI Object Storage bucket name.
        namespace_name: Object Storage namespace of the tenancy.

    Returns:
        A ready-to-use OCI storage instance.

    """
    backend = add_builtin_backend(name="oci_storage")
    return add_storage(
        name="oci",
        backend=backend,
        bucket_name=bucket_name,
        namespace_name=namespace_name,
    )


def add_storage_from_config(
    config: "StorageSectionConfig",
    backend_name: str,
    area: str | None = None,
    auth: "httpx.Auth | None" = None,
) -> StorageBase:
    """Build a fully-wired storage instance for a named backend from configuration.

    Args:
        config: Settings for every storage backend (nexus/s3/azure/oci).
        backend_name: Backend to build (``"nexus"``, ``"s3"``, ``"azure"`` or ``"oci"``).
        area: Logical area scoping the backend's storage (e.g. ``"bundles"`` /
            ``"artifacts"``). For S3 this is a folder prefix appended under the
            configured bucket/cluster; for Nexus/Azure/OCI it replaces the
            configured repository/container/bucket outright.
        auth: Authentication forwarded to backends that need it (Nexus).

    Returns:
        A ready-to-use storage instance for the requested backend.

    Raises:
        ValueError: If ``backend_name`` is not one of the known backends.

    """
    if backend_name == "nexus":
        settings = config.nexus
        return add_storage(
            "nexus",
            domain=settings.domain,
            repository=area or settings.repository,
            auth=auth,
        )
    if backend_name == "s3":
        settings = config.s3
        prefix = "/".join(segment for segment in (settings.cluster_name, area) if segment)
        return add_builtin_storage(
            "s3",
            bucket_name=settings.bucket_name,
            cluster_name=prefix or None,
        )
    if backend_name == "azure":
        settings = config.azure
        return add_builtin_storage(
            "azure",
            account_url=settings.account_url,
            container_name=area or settings.container_name,
        )
    if backend_name == "oci":
        settings = config.oci
        return add_builtin_storage(
            "oci",
            bucket_name=area or settings.bucket_name,
            namespace_name=settings.namespace_name,
        )

    msg = f"Unknown storage backend: {backend_name}"
    raise ValueError(msg)


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
