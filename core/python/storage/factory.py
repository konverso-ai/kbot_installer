"""Factory functions for creating bucket storage instances."""

from typing import TYPE_CHECKING, cast

from backend.factory import add_builtin_backend
from storage.base import StorageBackendEnum, StorageBase
from utils.factory import factory_function
from utils.factory.loader import factory_method

if TYPE_CHECKING:
    from collections.abc import Callable

    import httpx

    from credentials.oci_credentials import OciAuthMethod
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


def add_s3_storage(
    bucket_name: str,
    cluster_name: str | None = None,
    region_name: str | None = None,
) -> StorageBase:
    """Create an S3 storage instance using default boto3 credentials.

    Args:
        bucket_name: S3 bucket name.
        cluster_name: Optional root directory prefix inside the bucket.
        region_name: AWS region of the bucket. If None, ``AWS_DEFAULT_REGION``
            (or its default) is used.

    Returns:
        A ready-to-use S3 storage instance.

    """
    backend = add_builtin_backend(name="s3_storage", region_name=region_name)
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


def add_oci_storage(
    bucket_name: str,
    namespace_name: str,
    auth_method: "OciAuthMethod | None" = None,
) -> StorageBase:
    """Create an OCI Object Storage instance using the default OCI credentials.

    Args:
        bucket_name: OCI Object Storage bucket name.
        namespace_name: Object Storage namespace of the tenancy.
        auth_method: How to authenticate (``config_file``, ``instance_principal``
            or ``resource_principal``). If None, ``OCI_AUTH_METHOD`` (or its
            ``config_file`` default) is used.

    Returns:
        A ready-to-use OCI storage instance.

    """
    backend = add_builtin_backend(name="oci_storage", auth_method=auth_method)
    return add_storage(
        name="oci",
        backend=backend,
        bucket_name=bucket_name,
        namespace_name=namespace_name,
    )


def _resolve_backend(name: str) -> StorageBackendEnum:
    """Resolve a storage backend from its name or historical kbot provider name.

    Raises:
        ValueError: If ``name`` is not a known storage backend.

    """
    try:
        return StorageBackendEnum(name)
    except ValueError:
        msg = f"Unknown storage backend: {name}"
        raise ValueError(msg) from None


def _require_setting(get_config: "Callable[[str], str | None]", key: str) -> str:
    """Return a mandatory setting value.

    Raises:
        ValueError: If the setting is undefined or empty.

    """
    value = get_config(key)
    if not value:
        msg = f"Setting '{key}' is not defined."
        raise ValueError(msg)
    return value


def add_storage_from_settings(
    get_config: "Callable[[str], str | None]",
    provider: str | None = None,
) -> StorageBase:
    """Build the bucket storage described by kbot settings.

    Reads the connection settings of the selected provider (``kbot_storage_account``
    / ``storage_account_container_name`` for Azure, ``aws_s3_bucket_name`` /
    ``cluster_name`` / ``aws_s3_region`` for S3, ``oci_object_storage_bucket_name`` /
    ``oci_object_storage_namespace`` / ``oci_object_storage_auth`` for OCI).

    Args:
        get_config: Function returning the value of a setting by name, or None
            when the setting is undefined (e.g. kbot's ``Settings().GetConfig``).
        provider: Storage provider name, historical (``azure_blob``,
            ``amazon_s3``, ``oci_object_storage``) or backend name (``azure``,
            ``s3``, ``oci``). Defaults to the ``storage_bucket_provider`` setting.

    Returns:
        A ready-to-use storage instance.

    Raises:
        ValueError: If no provider is configured, if it is unknown or not a
            bucket provider (Nexus), or if a mandatory setting is undefined.

    """
    name = provider or get_config("storage_bucket_provider")
    if not name:
        msg = "No storage provider given and setting 'storage_bucket_provider' is not defined."
        raise ValueError(msg)

    backend = _resolve_backend(name)
    if backend is StorageBackendEnum.AZURE:
        return add_azure_storage(
            account_url=_require_setting(get_config, "kbot_storage_account"),
            container_name=_require_setting(get_config, "storage_account_container_name"),
        )
    if backend is StorageBackendEnum.S3:
        return add_s3_storage(
            bucket_name=_require_setting(get_config, "aws_s3_bucket_name"),
            cluster_name=get_config("cluster_name"),
            region_name=get_config("aws_s3_region"),
        )
    if backend is StorageBackendEnum.OCI:
        return add_oci_storage(
            bucket_name=_require_setting(get_config, "oci_object_storage_bucket_name"),
            namespace_name=_require_setting(get_config, "oci_object_storage_namespace"),
            auth_method=cast(
                "OciAuthMethod",
                get_config("oci_object_storage_auth") or "instance_principal",
            ),
        )
    msg = f"Storage backend '{backend.value}' cannot be built from settings."
    raise ValueError(msg)


def add_storage_from_config(
    config: "StorageSectionConfig",
    backend_name: str,
    area: str | None = None,
    auth: "httpx.Auth | None" = None,
) -> StorageBase:
    """Build a fully-wired storage instance for a named backend from configuration.

    Args:
        config: Settings for every storage backend (nexus/s3/azure/oci).
        backend_name: Backend to build (``"nexus"``, ``"s3"``, ``"azure"`` or ``"oci"``),
            or its historical kbot provider name (e.g. ``"azure_blob"``).
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
    backend = _resolve_backend(backend_name)
    if backend is StorageBackendEnum.NEXUS:
        settings = config.nexus
        return add_storage(
            "nexus",
            domain=settings.domain,
            repository=area or settings.repository,
            auth=auth,
        )
    if backend is StorageBackendEnum.S3:
        settings = config.s3
        prefix = "/".join(segment for segment in (settings.cluster_name, area) if segment)
        return add_builtin_storage(
            "s3",
            bucket_name=settings.bucket_name,
            cluster_name=prefix or None,
        )
    if backend is StorageBackendEnum.AZURE:
        settings = config.azure
        return add_builtin_storage(
            "azure",
            account_url=settings.account_url,
            container_name=area or settings.container_name,
        )
    settings = config.oci
    return add_builtin_storage(
        "oci",
        bucket_name=area or settings.bucket_name,
        namespace_name=settings.namespace_name,
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
