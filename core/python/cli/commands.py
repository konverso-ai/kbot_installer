"""Commandes CLI pour kbot-installer."""

import os
import secrets
from pathlib import Path

import click

from database.factory import add_db
from downloadable.bundle_downloadable import BundleDownloadable
from downloadable.product_downloadable import ProductDownloadable
from git.models import GitProvider
from git.provider.factory import add_selector_provider
from installable.workarea_installable import WorkareaInstallable
from installer_support.installation_table import InstallationTable
from installer_support.installer_service import InstallerService
from installer_support.installer_utils import version_to_branch
from installer_support.logging_config import setup_logging
from storage.base import StorageBackendEnum
from utils.product.build import Build
from utils.product.product import Product
from workarea.workarea import Workarea

# Default database password used when neither --db-password nor --no-password is given.
_DEFAULT_DB_PASSWORD = "kbot_db_pwd"  # noqa: S105

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
    help=(
        "Product name. Required in product mode. In bundle mode, defines the "
        "highest product level to install."
    ),
)
@click.option(
    "-v",
    "--version",
    required=True,
    type=str,
    help=(
        "Version to install. Product version in product mode, bundle version "
        "in bundle mode (e.g., '2025.03')."
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
    help=(
        "Specify which providers to use for installation. "
        "If not specified, all providers will be tried in order."
    ),
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
    version: str,
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
        kbot-installer download -b ev-basic-2025.03.0016 -v 2025.03 -p kbot -i ~/dev/installer
        kbot-installer download -b ev-basic-2025.03.0016 -v 2025.03 -p kbot --storage s3

    """
    if not product:
        msg = (
            "Option '-p/--product' is required when installing from a bundle."
            if bundle
            else "Option '-p/--product' is required when installing a product."
        )
        raise click.UsageError(msg)

    try:
        storage_backend = StorageBackendEnum(storage)
        installer_path = Path(installer_dir)

        if bundle:
            downloadable = BundleDownloadable(
                storage_name=storage_backend,
                name=bundle,
                installer_dir=installer_path,
                verbose=verbose,
            )
        else:
            product_obj = Product(
                name=product, build=Build(branch=version_to_branch(version))
            )
            selected_providers = (
                list(provider)
                if provider
                else [
                    "storage",
                    "github",
                    "bitbucket",
                ]
            )
            selector = add_selector_provider(provider_names=selected_providers)
            downloadable = ProductDownloadable(
                product=product_obj,
                provider=selector,
                table=InstallationTable(verbose=verbose),
                include_dependencies=not no_rec,
            )

        downloadable.download(installer_path)

    except click.UsageError:
        raise
    except Exception as e:
        click.echo(f"Error installing product: {e}", err=True)
        raise click.Abort from e


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
    help=(
        "Specify which providers to use for installation. "
        "If not specified, all providers will be tried in order."
    ),
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
    verbose: bool = False,
) -> None:
    r"""Install a kbot product or bundle: build the installer, workarea, and database.

    Without ``-b``, installs the given product at ``-v/--version`` together with
    all of its dependencies. With ``-b``, installs every product pinned by the
    bundle descriptor; ``-p`` then defines the top level product used to locate
    the database schema.

    The installer directory is built first (download), then the workarea is
    laid out from it, then the database is prepared and initialized. If
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
        _fetch_installer(
            installer_path=installer_path,
            product=product,
            version=version,
            bundle=bundle,
            provider=provider,
            storage_backend=storage_backend,
            verbose=verbose,
        )

        _build_workarea(installer_path=installer_path, workarea_path=workarea_path)

        generated_password = _build_database(
            installer_path=installer_path,
            workarea_path=workarea_path,
            product=product,
            db_host=db_host,
            db_port=db_port,
            db_user=db_user,
            db_password=db_password,
            db_name=db_name,
            no_password=no_password,
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


def _fetch_installer(
    installer_path: Path,
    product: str,
    version: str | None,
    bundle: str | None,
    provider: tuple[str, ...],
    storage_backend: StorageBackendEnum,
    *,
    verbose: bool,
) -> None:
    """Download the product (with dependencies) or bundle into the installer directory.

    Args:
        installer_path: Directory the products are downloaded into.
        product: Product name (top level product in bundle mode).
        version: Product version, required unless installing a bundle.
        bundle: Bundle name, or None to install a single product.
        provider: Providers to use for product mode; empty to try all in order.
        storage_backend: Storage backend used for bundle descriptors/artifacts,
            and for the "storage" provider in product mode.
        verbose: Whether to enable verbose logging.

    """
    if bundle:
        downloadable = BundleDownloadable(
            storage_name=storage_backend,
            name=bundle,
            installer_dir=installer_path,
            verbose=verbose,
        )
    else:
        if version is None:
            msg = "Option '-v/--version' is required when installing a product without '-b/--bundle'."
            raise click.UsageError(msg)
        product_obj = Product(name=product, build=Build(branch=version_to_branch(version)))
        selected_providers = list(provider) if provider else ["storage", "github", "bitbucket"]
        selector = add_selector_provider(provider_names=selected_providers)
        downloadable = ProductDownloadable(
            product=product_obj,
            provider=selector,
            table=InstallationTable(verbose=verbose),
            include_dependencies=True,
        )

    downloadable.download(installer_path)


def _build_workarea(installer_path: Path, workarea_path: Path) -> None:
    """Lay out the workarea from the products already present in the installer directory.

    Args:
        installer_path: Installer directory holding the downloaded products.
        workarea_path: Workarea directory to build.

    """
    service = InstallerService(installer_path)
    products = [Path(product.name) for product in service.load_products_from_disk()]

    workarea = Workarea(
        installer_root=installer_path,
        work_root=workarea_path,
        products=products,
    )
    WorkareaInstallable(workarea=workarea).install()


def _resolve_db_password(
    db_password: str | None, *, no_password: bool
) -> tuple[str, str | None]:
    """Resolve the database password to use, generating one if requested.

    Args:
        db_password: Password explicitly provided on the command line, if any.
        no_password: Whether a random password should be generated when
            ``db_password`` is not set.

    Returns:
        A tuple of ``(password, generated_password)``, where ``generated_password``
        is set only when a random password was generated (so it can be shown
        to the user).

    """
    if db_password:
        return db_password, None
    if no_password:
        generated = secrets.token_urlsafe(16)
        return generated, generated
    return _DEFAULT_DB_PASSWORD, None


def _build_database(
    installer_path: Path,
    workarea_path: Path,
    product: str,
    db_host: str | None,
    db_port: int,
    db_user: str,
    db_password: str | None,
    db_name: str,
    *,
    no_password: bool,
) -> str | None:
    """Prepare and initialize the product database.

    Uses an externally managed database when ``db_host`` is set, otherwise
    bootstraps a local, installer-owned PostgreSQL cluster under the workarea.

    Args:
        installer_path: Installer directory, used to locate the schema file.
        workarea_path: Workarea directory, used for the internal cluster's data/log paths.
        product: Top level product name, used to locate its ``db/init/db_schema.sql``.
        db_host: External Postgres host, or None to use an internal cluster.
        db_port: Postgres port.
        db_user: Postgres application user.
        db_password: Postgres application password, if explicitly provided.
        db_name: Postgres database name.
        no_password: Whether to generate a random password when db_password is unset.

    Returns:
        The randomly generated password, or None if no password was generated.

    """
    password, generated_password = _resolve_db_password(db_password, no_password=no_password)
    schema_path = installer_path / product / "db" / "init" / "db_schema.sql"

    if db_host:
        db = add_db(
            mode="external",
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=password,
            schema_path=schema_path,
            allow_schema_creation=True,
        )
    else:
        pg_dir = os.environ.get("PG_DIR")
        if not pg_dir:
            msg = "The 'PG_DIR' environment variable must be set to install a local database."
            raise click.UsageError(msg)

        db = add_db(
            mode="internal",
            host="localhost",
            port=db_port,
            database=db_name,
            user=db_user,
            password=password,
            schema_path=schema_path,
            pg_dir=Path(pg_dir),
            pg_data=workarea_path / "var" / "db",
            log_path=workarea_path / "logs" / "postgres.log",
            admin_user="postgres",
            admin_password=os.environ.get("PG_ADMIN_PASSWORD", "postgres"),
        )

    db.prepare()
    db.initialize()
    return generated_password


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
def list_products(
    *, tree: bool = False, installer_dir: str, verbose: bool = False
) -> None:
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
