"""Factory for creating DownloadableBase instances by name."""

from typing import TYPE_CHECKING, cast

from downloadable.base import DownloadableBase
from downloadable.bundle_downloadable import BundleDownloadable
from downloadable.product_downloadable import ProductDownloadable
from git.provider.factory import add_selector_provider
from installer_support.installation_table import InstallationTable
from installer_support.installer_utils import version_to_branch
from utils.factory.loader import factory_method
from utils.product.build import Build
from utils.product.product import Product

if TYPE_CHECKING:
    from pathlib import Path

    from storage.base import StorageBackendEnum

# Default provider order tried in product mode when none is explicitly requested.
_DEFAULT_PROVIDER_NAMES: tuple[str, ...] = ("storage", "github", "bitbucket")


def add_downloadable(name: str, **kwargs: object) -> DownloadableBase:
    """Create a downloadable instance by name.

    Args:
        name: Name of the downloadable to create (e.g. "product", "bundle").
        **kwargs: Additional arguments to pass to the downloadable constructor.

    Returns:
        An instance of the specified downloadable.

    """
    return cast(
        "DownloadableBase",
        factory_method(name=name, package="downloadable", **kwargs),
    )


def build_downloadable(
    *,
    product: str,
    version: str | None,
    bundle: str | None,
    installer_path: "Path",
    provider: tuple[str, ...] = (),
    storage_backend: "StorageBackendEnum",
    include_dependencies: bool,
    verbose: bool = False,
) -> DownloadableBase:
    """Build the downloadable for a product (with dependencies) or a bundle.

    Args:
        product: Product name (top level product in bundle mode).
        version: Product version, required unless ``bundle`` is set.
        bundle: Bundle name, or None to download a single product.
        installer_path: Directory the bundle descriptor is looked up from
            (bundle mode only; product mode resolves the products relative to
            the path passed to ``download()``).
        provider: Providers to use in product mode; empty to try the default
            order (``storage``, ``github``, ``bitbucket``).
        storage_backend: Storage backend used for bundle descriptors/artifacts,
            and for the "storage" provider in product mode.
        include_dependencies: Whether ``download()`` should also fetch the
            product's dependencies (ignored in bundle mode, which always
            follows the bundle descriptor).
        verbose: Whether to enable verbose logging.

    Returns:
        A ``DownloadableBase`` ready to have ``.download(installer_path)`` called.

    Raises:
        ValueError: If ``bundle`` is None and ``version`` was not provided.

    """
    if bundle:
        return BundleDownloadable(
            storage_name=storage_backend,
            name=bundle,
            installer_dir=installer_path,
            verbose=verbose,
        )

    if version is None:
        msg = "'version' is required when building a downloadable for a product without a bundle."
        raise ValueError(msg)

    product_obj = Product(name=product, build=Build(branch=version_to_branch(version)))
    selected_providers = list(provider) if provider else list(_DEFAULT_PROVIDER_NAMES)
    selector = add_selector_provider(provider_names=selected_providers)
    return ProductDownloadable(
        product=product_obj,
        provider=selector,
        table=InstallationTable(verbose=verbose),
        include_dependencies=include_dependencies,
    )
