"""Commandes CLI pour kbot-installer."""

import logging
from pathlib import Path

import click

from kbot_installer.core import InstallerService

# Configurer le niveau de log pour réduire les messages verbeux
logging.basicConfig(
    level=logging.WARNING, format="%(levelname)s: %(name)s: %(message)s"
)


def _parse_providers(uses: str | None) -> list[str] | None:
    """Parse comma-separated provider string into a list of providers.

    Args:
        uses: Comma-separated string of providers (e.g., 'github,bitbucket' or 'nexus').

    Returns:
        List of provider names in lowercase, or None if uses is None.

    Raises:
        click.Abort: If any provider is invalid.

    """
    if not uses:
        return None

    # Split by comma and strip whitespace
    providers_list = [p.strip() for p in uses.split(",")]

    # Validate providers
    valid_providers = {"nexus", "github", "bitbucket"}
    invalid_providers = [p for p in providers_list if p.lower() not in valid_providers]
    if invalid_providers:
        click.echo(
            f"Error: Invalid providers: {', '.join(invalid_providers)}",
            err=True,
        )
        click.echo("Valid providers are: nexus, github, bitbucket", err=True)
        raise click.Abort

    # Convert to lowercase for consistency
    return [p.lower() for p in providers_list]


@click.group()
@click.version_option(version="0.1.0", prog_name="kbot-installer")
def cli() -> None:
    """Kbot Installer - A tool for installing and managing kbot products.

    This CLI provides commands to install, list, and explore kbot products
    and their dependencies.
    """


@cli.command()
@click.option(
    "-i",
    "--installer-dir",
    type=click.Path(),
    default=lambda: str(Path.home() / "dev" / "installer"),
    help="Installation directory (default: $HOME/dev/installer)",
)
@click.option(
    "-v",
    "--version",
    required=True,
    type=str,
    help="Version of the product to install (e.g., '2025.03', 'dev', 'master')",
)
@click.option(
    "-p", "--product", required=True, type=str, help="Name of the product to install"
)
@click.option(
    "-r",
    "--no-rec",
    is_flag=True,
    default=False,
    help="Skip installing product dependencies (default: False)",
)
@click.option(
    "--uses",
    type=str,
    help="Specify which providers to use for installation. Comma-separated list (e.g., 'github,bitbucket' or 'nexus'). If not specified, all providers will be tried in order.",
)
def installer(
    installer_dir: str,
    version: str,
    product: str,
    *,
    no_rec: bool = False,
    uses: str | None = None,
) -> None:
    """Install a kbot product with specified version.

    This command installs the specified product at the given version.
    By default, it will also install all dependencies unless --no-rec is used.
    Use --uses to specify which providers to use for installation.

    Examples:
        kbot-installer installer -v 2025.03 -p jira
        kbot-installer installer -v dev -p jira --no-rec
        kbot-installer installer -i /custom/path -v master -p ithd
        kbot-installer installer -v 2025.03 -p jira --uses github,bitbucket
        kbot-installer installer -v dev -p kbot-latest-dev --uses nexus

    """
    try:
        # Parse comma-separated providers if specified
        selected_providers = _parse_providers(uses)

        service = InstallerService(installer_dir, providers=selected_providers)

        click.echo(
            f"Installing product '{product}' version '{version}' to '{installer_dir}'"
        )

        # Show which providers will be used
        if selected_providers:
            click.echo(f"Using providers: {', '.join(selected_providers)}")
        else:
            click.echo("Using all available providers: nexus, github, bitbucket")

        # Install the product (will load products and dependencies automatically)
        include_dependencies = not no_rec
        if include_dependencies:
            click.echo("Loading product definitions and dependencies...")
        else:
            click.echo("Loading product definitions (skipping dependencies)...")

        service.install(product, version, include_dependencies=include_dependencies)

        # Display summary (results are already displayed during installation)
        installation_table = service.get_installation_table()
        click.echo(f"\n{installation_table.get_summary()}")

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
def list_products(*, tree: bool = False, installer_dir: str) -> None:
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
        output = service.list_products(as_tree=tree)
        click.echo(output)

    except Exception as e:
        click.echo(f"Error listing products: {e}", err=True)
        raise click.Abort from e


@cli.command()
@click.option(
    "-i",
    "--installer-dir",
    type=click.Path(),
    default=lambda: str(Path.home() / "dev" / "installer"),
    help="Installation directory (default: $HOME/dev/installer)",
)
@click.option(
    "-v",
    "--version",
    type=str,
    help="Version of the product to repair (e.g., '2025.03', 'dev', 'master'). If not specified, will try to detect from existing installation.",
)
@click.option(
    "-p", "--product", required=True, type=str, help="Name of the product to repair"
)
def repair(
    installer_dir: str, version: str | None = None, product: str | None = None
) -> None:
    """Repair a kbot product by reinstalling missing dependencies.

    This command detects missing products in the installer directory and
    reinstalls them. It's useful when some products or dependencies
    have been accidentally deleted or corrupted.

    Examples:
        kbot-installer repair -p kbot-latest-dev
        kbot-installer repair -p kbot -v 2025.03
        kbot-installer repair -p kbot -i /custom/path

    """
    try:
        service = InstallerService(installer_dir)

        # Check if installer directory exists
        if not Path(installer_dir).exists():
            click.echo("Installer directory does not exist. Nothing to repair.")
            return

        click.echo(f"Repairing product '{product}' in '{installer_dir}'")

        # Repair the product
        repaired_products = service.repair(product, version=version)

        if repaired_products:
            click.echo(f"✅ Successfully repaired {len(repaired_products)} products:")
            for repaired_product in repaired_products:
                click.echo(f"  - {repaired_product}")
        else:
            click.echo("✅ No missing products detected. Everything is up to date.")

    except Exception as e:
        click.echo(f"Error repairing product: {e}", err=True)
        raise click.Abort from e
