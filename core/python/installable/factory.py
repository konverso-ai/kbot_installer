"""Factory for creating installable products."""

from typing import TYPE_CHECKING, Literal, cast

from utils.factory.factory import factory_class
from utils.product import Build, Categories, Category, LocDisplayMapper, Parent, Parents, Product
from utils.version import Version

if TYPE_CHECKING:
    from installable.product_installable import BuildDetails, ProductInstallable


def create_installable(
    name: str,
    version: str = "",
    build: str | None = None,
    date: str | None = None,
    product_type: str = "solution",
    type: str | None = None,
    docs: list[str] | None = None,
    env: str = "dev",
    parents: list[str] | None = None,
    categories: list[str] | None = None,
    license_info: str | None = None,
    license: str | None = None,
    display: dict[str, dict[str, str]] | None = None,
    build_details: "BuildDetails | None" = None,
    providers: list[str] | None = None,
    branch: str | None = None,
) -> "ProductInstallable":
    """Create a ProductInstallable instance.

    This is the factory method for creating installable products. It currently
    creates ProductInstallable instances, but could be extended to support
    other types in the future.

    Args:
        name: Product name.
        version: Product version.
        build: Build information.
        date: Build date.
        product_type: Product type (solution, framework, customer).
        docs: List of documentation references.
        env: Environment (dev, prod). If branch is specified, this is forced to "dev".
        parents: List of parent product names (dependencies).
        categories: List of product categories.
        license_info: License information.
        display: Multilingual display information.
        build_details: Detailed build information.
        providers: List of provider names.
        branch: Specific branch to use. If provided, env is forced to "dev" and
               this branch is used instead of calculating from version.

    Returns:
        ProductInstallable instance.

    """
    effective_env: Literal["dev", "prod"] = "dev" if branch else cast("Literal['dev', 'prod']", env)
    effective_type = type if type is not None else product_type
    effective_license = license if license is not None else license_info

    build_obj: Build | None = None
    if build_details:
        build_obj = Build(
            timestamp=build_details.get("timestamp", ""),
            branch=build_details.get("branch", ""),
            commit=build_details.get("commit", ""),
        )
    elif build:
        build_obj = Build(timestamp=build)

    product = Product(
        name=name,
        version=Version.parse(version),
        doc=",".join(docs) if docs else None,
        build=build_obj,
        date=date or "",
        type=effective_type,
        parents=(
            Parents(parent=[Parent(name=parent_name) for parent_name in parents])
            if parents
            else None
        ),
        categories=(
            Categories(
                category=[Category(name=category_name) for category_name in categories]
            )
            if categories
            else None
        ),
        license=effective_license,
        display=LocDisplayMapper.model_validate(display) if display is not None else None,
    )

    installable_kwargs = {
        "product": product,
        "env": effective_env,
        "providers": providers or ["storage", "github", "bitbucket"],
        "branch": branch,
    }

    cls = factory_class(
        name="product",
        package="installable",
    )

    return cast("ProductInstallable", cls(**installable_kwargs))
