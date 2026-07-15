"""Commandes CLI pour kbot-installer."""

from pathlib import Path

import click

from downloadable.bundle_downloadable import BundleDownloadable
from downloadable.product_downloadable import ProductDownloadable
from git.models import GitProvider
from git.provider.factory import add_provider
from installer_support.installation_table import InstallationTable
from installer_support.installer_service import InstallerService
from installer_support.installer_utils import version_to_branch
from installer_support.logging_config import setup_logging
from storage.base import StorageBackendEnum
from utils.product.build import Build
from utils.product.product import Product

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
            selector = add_provider(name="selector", providers=selected_providers)
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
