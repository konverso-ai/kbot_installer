"""Factory for creating installable products."""

from kbot_installer.core.factory.factory import factory_class
from kbot_installer.core.product.installable_base import InstallableBase


def create_installable(
    name: str,
    version: str = "",
    build: str | None = None,
    date: str | None = None,
    product_type: str = "solution",
    docs: list[str] | None = None,
    env: str = "dev",
    parents: list[str] | None = None,
    categories: list[str] | None = None,
    license_info: str | None = None,
    display: dict | None = None,
    build_details: dict | None = None,
    providers: list[str] | None = None,
) -> InstallableBase:
    """Create an InstallableBase instance.

    This is the factory method for creating installable products. It currently
    creates InstallableProduct instances, but could be extended to support
    other types in the future.

    Args:
        name: Product name.
        version: Product version.
        build: Build information.
        date: Build date.
        product_type: Product type (solution, framework, customer).
        docs: List of documentation references.
        env: Environment (dev, prod).
        parents: List of parent product names (dependencies).
        categories: List of product categories.
        license_info: License information.
        display: Multilingual display information.
        build_details: Detailed build information.
        providers: List of provider names.

    Returns:
        InstallableBase instance.

    """
    # Prepare kwargs for InstallableProduct constructor
    product_kwargs = {
        "name": name,
        "version": version,
        "build": build,
        "date": date,
        "type": product_type,
        "docs": docs or [],
        "env": env,
        "parents": parents or [],
        "categories": categories or [],
        "license": license_info,
        "display": display,
        "build_details": build_details,
        "providers": providers or ["nexus", "github", "bitbucket"],
    }

    # Get the class using factory_class
    cls = factory_class(
        name="installable",
        package="kbot_installer.core.product",
    )

    # Instantiate with the product kwargs
    return cls(**product_kwargs)
