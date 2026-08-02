"""Commandes CLI pour kbot-installer."""

import os
from pathlib import Path

import click

from database.factory import build_database
from database.utils import resolve_db_password
from downloadable.factory import build_downloadable
from git.models import GitProvider
from installable.dependency_graph import DependencyGraph
from installable.factory import build_workarea
from installer_support.installer_service import InstallerService
from installer_support.logging_config import setup_logging
from installer_support.python_requirements import install_product_python_requirements
from installer_support.thirdparty_env import prepend_thirdparty_ld_library_path, resolve_pg_dir_str
from storage.base import StorageBackendEnum

# Setup logging from configuration file
setup_logging()


_PROVIDER_CHOICES = click.Choice(
    [provider.value for provider in GitProvider],
    case_sensitive=False,
)
_STORAGE_CHOICES = click.Choice(
    [backend.value for backend in StorageBackendEnum],
    case_sensitive=False,
)


@click.group(invoke_without_command=True)
@click.version_option(version="0.1.0", prog_name="kbot-installer")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Kbot Installer - A tool for installing and managing kbot products.

    This CLI provides commands to download and list kbot products
    and their dependencies.
    """
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        ctx.exit()


@cli.command(name="download")
@click.option(
    "-b",
    "--bundle",
    type=str,
    default=None,
    help="Bundle name. When set, installs products from a bundle descriptor in storage.",
)
@click.option(
    "-p",
    "--product",
    type=str,
    default=None,
    help=("Product name. Required in product mode. In bundle mode, defines the highest product level to install."),
)
@click.option(
    "-v",
    "--version",
    type=str,
    default=None,
    help=(
        "Product version to download (e.g., '2025.03-dev'). Required unless "
        "'-b/--bundle' is used, since a bundle already pins each product's version."
    ),
)
@click.option(
    "-i",
    "--installer-dir",
    type=click.Path(),
    default=lambda: str(Path.home() / "dev" / "installer"),
    help="Installation directory (default: $HOME/dev/installer)",
)
@click.option(
    "-r",
    "--no-rec",
    is_flag=True,
    default=False,
    help="Skip installing product dependencies (default: False)",
)
@click.option(
    "--provider",
    type=_PROVIDER_CHOICES,
    multiple=True,
    help=("Specify which providers to use for installation. If not specified, all providers will be tried in order."),
)
@click.option(
    "--storage",
    type=_STORAGE_CHOICES,
    default=StorageBackendEnum.NEXUS.value,
    show_default=True,
    help="Storage backend to use when the storage provider is selected.",
)
@click.option(
    "-V",
    "--verbose",
    is_flag=True,
    default=False,
    help="Show detailed output (skipped products, provider download details).",
)
def download(
    installer_dir: str,
    version: str | None,
    product: str | None,
    bundle: str | None,
    *,
    no_rec: bool = False,
    provider: tuple[str, ...] = (),
    storage: str = StorageBackendEnum.NEXUS.value,
    verbose: bool = False,
) -> None:
    """Download kbot products from a product version or a bundle descriptor.

    Without ``-b``, downloads the specified product at the given version.
    With ``-b``, downloads products pinned in the bundle descriptor from storage.
    ``-p`` is then required and defines the highest product level to install.

    By default, dependencies are downloaded unless ``--no-rec`` is used.

    Examples:
        kbot-installer download -v 2025.03 -p jira
        kbot-installer download -v dev -p jira --no-rec
        kbot-installer download -i /custom/path -v master -p ithd
        kbot-installer download -v 2025.03 -p jira --provider github --provider bitbucket
        kbot-installer download -v dev -p kbot-latest-dev --provider storage --storage s3
        kbot-installer download -b ev-basic-2025.03.0016 -p kbot -i ~/dev/installer
        kbot-installer download -b ev-basic-2025.03.0016 -p kbot --storage s3

    """
    if not product:
        msg = (
            "Option '-p/--product' is required when installing from a bundle."
            if bundle
            else "Option '-p/--product' is required when installing a product."
        )
        raise click.UsageError(msg)

    if not bundle and not version:
        msg = "Option '-v/--version' is required when downloading a product without '-b/--bundle'."
        raise click.UsageError(msg)

    try:
        storage_backend = StorageBackendEnum(storage)
        installer_path = Path(installer_dir)

        downloadable = build_downloadable(
            product=product,
            version=version,
            bundle=bundle,
            installer_path=installer_path,
            provider=provider,
            storage_backend=storage_backend,
            include_dependencies=not no_rec,
            verbose=verbose,
        )
        downloadable.download(installer_path)

    except click.UsageError:
        raise
    except Exception as e:
        click.echo(f"Error installing product: {e}", err=True)
        raise click.Abort from e


def _resolve_internal_pg_dir(installer_path: Path) -> Path:
    """Resolve PG_DIR for an internal database cluster, or raise a usage error.

    Args:
        installer_path: Installer directory holding the downloaded products.

    Returns:
        The resolved PG_DIR path.

    Raises:
        click.UsageError: If PG_DIR cannot be resolved from the environment
            or the downloaded 3rdparty product.

    """
    pg_dir_str = os.environ.get("PG_DIR") or resolve_pg_dir_str(installer_path)
    if not pg_dir_str:
        msg = (
            "Unable to locate PostgreSQL: set the 'PG_DIR' environment variable, "
            f"or ensure '{installer_path / '3rdparty' / 'versions.env'}' exists and "
            "defines 'PG_DIR'."
        )
        raise click.UsageError(msg)
    return Path(pg_dir_str)


def _build_schema_paths(installer_path: Path) -> list[Path]:
    """Build the ordered list of product schema files to apply.

    Every product downloaded alongside the top level product (i.e. every
    subdirectory of ``installer_path`` holding a ``description.xml``) may ship
    its own ``db/init/db_schema.sql``. They are returned in dependency order
    (a product's dependencies before the product itself) so that a schema
    referencing tables defined by a dependency can be applied safely.

    Args:
        installer_path: Installer directory holding the downloaded products.

    Returns:
        Ordered list of ``db/init/db_schema.sql`` paths, one per discovered
        product. Products without a schema file are still listed;
        ``build_database`` skips missing files.

    """
    products = InstallerService(installer_dir=installer_path).load_products_from_disk()
    graph = DependencyGraph(products)
    return [installer_path / name / "db" / "init" / "db_schema.sql" for name in graph.get_topological_order()]


@cli.command(name="install")
@click.option(
    "-b",
    "--bundle",
    type=str,
    default=None,
    help="Bundle name. When set, installs products from a bundle descriptor in storage.",
)
@click.option(
    "-p",
    "--product",
    type=str,
    required=True,
    help="Top level product to install. Its dependencies are always installed too.",
)
@click.option(
    "-v",
    "--version",
    type=str,
    default=None,
    help=(
        "Product version to install (e.g., '2025.03-dev'). Required unless "
        "'-b/--bundle' is used, since a bundle already pins each product's version."
    ),
)
@click.option(
    "-i",
    "--installer-dir",
    type=click.Path(),
    default=lambda: str(Path.home() / "dev" / "installer"),
    help="Installer directory (default: $HOME/dev/installer)",
)
@click.option(
    "-w",
    "--workarea-dir",
    type=click.Path(),
    default=lambda: str(Path.home() / "dev" / "work"),
    help="Workarea directory (default: $HOME/dev/work)",
)
@click.option(
    "--secret",
    type=str,
    required=True,
    help="Admin secret password for the installed product.",
)
@click.option(
    "--provider",
    type=_PROVIDER_CHOICES,
    multiple=True,
    help=("Specify which providers to use for installation. If not specified, all providers will be tried in order."),
)
@click.option(
    "--storage",
    type=_STORAGE_CHOICES,
    default=StorageBackendEnum.NEXUS.value,
    show_default=True,
    help="Storage backend to use when the storage provider is selected.",
)
@click.option(
    "--db-host",
    type=str,
    default=None,
    help="Postgres hostname or IP. When set, an externally managed database is used.",
)
@click.option(
    "--db-port",
    type=int,
    default=5432,
    show_default=True,
    help="Postgres port.",
)
@click.option(
    "--db-user",
    type=str,
    default="kbot_db_user",
    show_default=True,
    help="Postgres user.",
)
@click.option(
    "--db-password",
    type=str,
    default=None,
    help="Postgres password (default: 'kbot_db_pwd', unless --no-password is used).",
)
@click.option(
    "--db-name",
    type=str,
    default="kbot_db",
    show_default=True,
    help="Postgres database name.",
)
@click.option(
    "--no-password",
    is_flag=True,
    default=False,
    help="Generate a random database password instead of using --db-password.",
)
@click.option(
    "--skip-python-requirements",
    is_flag=True,
    default=False,
    help=(
        "Skip installing each solution/customer product's requirements.txt "
        "into the 3rdparty Python (via the downloaded kbot/bin/pip3.sh)."
    ),
)
@click.option(
    "-V",
    "--verbose",
    is_flag=True,
    default=False,
    help="Show detailed output (skipped products, provider download details).",
)
def install(
    installer_dir: str,
    workarea_dir: str,
    product: str,
    secret: str,
    version: str | None,
    bundle: str | None,
    *,
    provider: tuple[str, ...] = (),
    storage: str = StorageBackendEnum.NEXUS.value,
    db_host: str | None = None,
    db_port: int = 5432,
    db_user: str = "kbot_db_user",
    db_password: str | None = None,
    db_name: str = "kbot_db",
    no_password: bool = False,
    skip_python_requirements: bool = False,
    verbose: bool = False,
) -> None:
    r"""Install a kbot product or bundle: build the installer, workarea, and database.

    Without ``-b``, installs the given product at ``-v/--version`` together with
    all of its dependencies. With ``-b``, installs every product pinned by the
    bundle descriptor; ``-p`` then defines the top level product.

    The installer directory is built first (download), then the workarea is
    laid out from it, then the database is prepared and initialized: every
    downloaded product's ``db/init/db_schema.sql`` is applied, in dependency
    order (dependencies before the products that depend on them). If
    ``--workarea-dir`` already exists, the installation is cancelled before
    anything is downloaded or built.

    Examples:
        kbot-installer install -b ev-basic-00018 -p site-konverso --secret 'K0nversOK!' \\
            --workarea-dir ~/dev/work --installer-dir ~/dev/installer
        kbot-installer install -p site-konverso -v 2025.03-dev --secret 'K0nversOK!' \\
            --workarea-dir ~/dev/work --installer-dir ~/dev/installer

    """
    if not bundle and not version:
        msg = "Option '-v/--version' is required when installing a product without '-b/--bundle'."
        raise click.UsageError(msg)

    installer_path = Path(installer_dir)
    workarea_path = Path(workarea_dir)

    if workarea_path.exists():
        click.echo(
            f"Workarea directory '{workarea_path}' already exists. Installation cancelled.",
            err=True,
        )
        raise click.Abort

    # secret is captured for the future admin data "load" step; not applied yet.
    _ = secret

    try:
        storage_backend = StorageBackendEnum(storage)
        downloadable = build_downloadable(
            product=product,
            version=version,
            bundle=bundle,
            installer_path=installer_path,
            provider=provider,
            storage_backend=storage_backend,
            include_dependencies=True,
            verbose=verbose,
        )
        downloadable.download(installer_path)

        build_workarea(installer_path=installer_path, workarea_path=workarea_path).install()

        if not skip_python_requirements:
            install_product_python_requirements(installer_path)

        password, generated_password = resolve_db_password(db_password, no_password=no_password)
        schema_paths = _build_schema_paths(installer_path)

        pg_dir: Path | None = None
        if not db_host:
            pg_dir = _resolve_internal_pg_dir(installer_path)
            prepend_thirdparty_ld_library_path(installer_path)

        build_database(
            schema_paths=schema_paths,
            db_host=db_host,
            db_port=db_port,
            db_user=db_user,
            password=password,
            db_name=db_name,
            workarea_path=workarea_path,
            pg_dir=pg_dir,
            admin_password=os.environ.get("PG_ADMIN_PASSWORD", "postgres"),
        )
        if generated_password is not None:
            click.echo(f"Generated database password for '{db_user}': {generated_password}")

        click.echo("Installation completed successfully.")

    except click.UsageError:
        raise
    except click.Abort:
        raise
    except Exception as e:
        click.echo(f"Error installing product: {e}", err=True)
        raise click.Abort from e


@cli.command(name="list")
@click.option(
    "--tree",
    is_flag=True,
    help="Show products as dependency tree",
)
@click.option(
    "-i",
    "--installer-dir",
    type=click.Path(),
    default=lambda: str(Path.home() / "dev" / "installer"),
    help="Installation directory (default: $HOME/dev/installer)",
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Show all subtrees even if already displayed (default: hide redundant subtrees)",
)
def list_products(*, tree: bool = False, installer_dir: str, verbose: bool = False) -> None:
    """List installed kbot products.

    This command displays a list of all products that are currently installed
    in the installer directory, including their versions and status.
    Use --tree to show as dependency tree.
    """
    try:
        service = InstallerService(installer_dir)
        # Check if installer directory exists
        if not Path(installer_dir).exists():
            click.echo("Installer directory does not exist. No products installed.")
            return

        # List the installed products
        output = service.list_products(as_tree=tree, verbose=verbose)
        click.echo(output)

    except Exception as e:
        click.echo(f"Error listing products: {e}", err=True)
        raise click.Abort from e
