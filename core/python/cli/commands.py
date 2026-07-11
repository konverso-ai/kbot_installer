"""Commandes CLI pour kbot-installer."""

import shutil
import subprocess
from pathlib import Path
from typing import cast

import click
from git.models import GitProvider
from installable.factory import create_installable
from installable.product_installable import ProductInstallable
from installer_support.installer_service import InstallerService
from installer_support.logging_config import setup_logging
from storage.base import StorageBackend
from workarea.workarea import Workarea

# Setup logging from configuration file
setup_logging()

_PROVIDER_CHOICES = click.Choice(
    [provider.value for provider in GitProvider],
    case_sensitive=False,
)
_STORAGE_CHOICES = click.Choice(
    [backend.value for backend in StorageBackend],
    case_sensitive=False,
)


@click.group(invoke_without_command=True)
@click.version_option(version="0.1.0", prog_name="kbot-installer")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Kbot Installer - A tool for installing and managing kbot products.

    This CLI provides commands to install, list, and explore kbot products
    and their dependencies.
    """
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        ctx.exit()


@cli.command()
@click.option(
    "-w",
    "--workarea",
    type=click.Path(),
    default=lambda: str(Path.cwd()),
    help="Workarea directory path (default: current directory)",
)
def init(*, workarea: str) -> None:
    """Initialize a UV workspace and lay out the workarea directory structure.

    This command creates a UV workspace in the specified directory and sets up
    the workarea structure (conf, logs, var, products, ...). Products should be
    installed separately using the 'download' command.

    \b
    Examples:
        kbot-installer init
        kbot-installer init -w /path/to/workarea
    """  # noqa: D301
    try:
        workarea_path = Path(workarea).resolve()

        # Create workarea directory if it doesn't exist
        workarea_path.mkdir(parents=True, exist_ok=True)

        # Initialize UV workspace
        click.echo(f"Creating UV workspace in {workarea_path}")

        def _abort_uv_not_found() -> None:
            click.echo(
                "Error: 'uv' command not found. Please install UV first.",
                err=True,
            )
            raise click.Abort from None  # noqa: TRY301

        def _handle_uv_init_error(e: subprocess.CalledProcessError) -> None:
            click.echo(
                f"Error initializing UV workspace: {e.stderr or e.stdout}",
                err=True,
            )
            raise click.Abort from e  # noqa: TRY301

        uv_executable = shutil.which("uv")
        if uv_executable is None:
            _abort_uv_not_found()
        assert uv_executable is not None

        try:
            subprocess.run(  # noqa: S603
                [uv_executable, "init"],
                cwd=str(workarea_path),
                check=True,
            )
            click.echo("✅ UV workspace initialized successfully")
        except subprocess.CalledProcessError as e:
            _handle_uv_init_error(e)

        # Lay out the workarea structure (no products yet, install adds them later)
        workarea_installable = create_installable(
            "workarea",
            workarea=Workarea(
                installer_root=workarea_path,
                work_root=workarea_path,
                products=[],
            ),
        )
        workarea_installable.install()

        click.echo(f"✅ Workarea initialized successfully at {workarea_path}")

    except Exception as e:
        click.echo(f"Error initializing workarea: {e}", err=True)
        raise click.Abort from e


@cli.command()
@click.option(
    "-n",
    "--name",
    required=True,
    type=str,
    help="Name of the product to add",
)
@click.option(
    "-v",
    "--version",
    type=str,
    default="",
    help="Version of the product (e.g., '2025.03', 'dev', 'master'). If not specified, version is empty.",
)
@click.option(
    "-b",
    "--branch",
    type=str,
    default=None,
    help="Specific branch to use (overrides version). If specified, env is forced to 'dev'.",
)
@click.option(
    "-e",
    "--env",
    type=click.Choice(["dev", "prod"], case_sensitive=False),
    default="dev",
    help="Environment type (dev or prod)",
)
@click.option(
    "--installer-dir",
    type=click.Path(),
    default=lambda: str(Path("dev") / "installer"),
    help="Installer directory where products are cloned (default: dev/installer)",
)
@click.option(
    "--workarea-dir",
    type=click.Path(),
    default=lambda: str(Path("dev") / "work"),
    help="Workarea directory where products are installed (default: dev/work)",
)
@click.option(
    "-r",
    "--no-rec",
    is_flag=True,
    default=False,
    help="Skip installing product dependencies (default: False)",
)
def add(
    name: str,
    version: str = "",
    branch: str | None = None,
    env: str = "dev",
    installer_dir: str = "",
    workarea_dir: str = "",
    *,
    no_rec: bool = False,
) -> None:
    """Add a product to the installer and install it in the workarea.

    This command creates an installable product, clones it to the installer directory,
    and installs it in the workarea directory.

    Providers are selected based on environment:
    - dev: ['bitbucket', 'github']
    - prod: ['nexus', 'bitbucket']

    \b
    Examples:
        kbot-installer add -n jira -v 2025.03
        kbot-installer add -n kbot -b master --env dev
        kbot-installer add -n jira -v dev --env prod --installer-dir /custom/installer
        kbot-installer add -n ithd -v 2025.03 --no-rec

    """  # noqa: D301
    try:
        installer_path = Path(installer_dir).resolve()
        workarea_path = Path(workarea_dir).resolve()

        # Check if product already exists in installer directory
        product_dir = installer_path / name
        description_file = product_dir / "description.xml"
        if product_dir.exists() and description_file.exists():
            click.echo(
                f"Product '{name}' already exists in {installer_path}. Skipping.",
            )
            return

        # Determine providers based on environment
        providers = ["bitbucket", "github"] if env == "dev" else ["nexus", "bitbucket"]

        click.echo(f"Adding product '{name}' with providers: {', '.join(providers)}")

        # Create installable product
        installable = cast(
            ProductInstallable,
            create_installable(
                "product",
                name=name,
                version=version,
                branch=branch,
                env=env,
                providers=providers,
            ),
        )

        # Ensure installer directory exists
        installer_path.mkdir(parents=True, exist_ok=True)

        # Clone product to installer directory
        click.echo(f"Downloading product '{name}' to {installer_path}")
        installable.download(installer_path, dependencies=not no_rec)

        # Ensure installable has dirname set after clone
        if not installable.dirname:
            product_dir = installer_path / name
            if product_dir.exists() and (product_dir / "description.xml").exists():
                installable.dirname = product_dir.resolve()
                click.echo(f"Set dirname to {installable.dirname}")
            else:
                click.echo(
                    f"Warning: Product directory not found at {product_dir}",
                    err=True,
                )

        # Ensure workarea directory exists
        workarea_path.mkdir(parents=True, exist_ok=True)

        # Install product to workarea
        click.echo(f"Installing product '{name}' to {workarea_path}")

        installable.install(
            workarea_path,
            dependencies=not no_rec,
            installer_path=installer_path,
        )

        # Verify installation worked
        # Check if any files were created in workarea (besides standard dirs)
        workarea_contents = list(workarea_path.iterdir())
        # Filter out common directories that might be created by other processes
        significant_contents = [
            item
            for item in workarea_contents
            if item.name not in ["__pycache__", ".git", "logs", "var"]
        ]

        if significant_contents:
            click.echo(
                f"✅ Product '{name}' added and installed successfully to {workarea_path}"
            )
        else:
            click.echo(
                f"⚠️  Product '{name}' cloned, but no files were installed in workarea.",
            )
            click.echo(
                "This may be normal if the product has no [work] section in pyproject.toml",
            )

    except Exception as e:
        click.echo(f"Error adding product: {e}", err=True)
        raise click.Abort from e


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
    default=StorageBackend.NEXUS.value,
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
    storage: str = StorageBackend.NEXUS.value,
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
        kbot-installer download -b release-2025.03 -v 2025.03 -p kbot -i ~/dev/installer
        kbot-installer download -b release-2025.03 -v 2025.03 -p kbot --storage s3 --no-rec

    """
    try:
        if bundle:
            if not product:
                raise click.UsageError(
                    "Option '-p/--product' is required when installing from a bundle."
                )
        elif not product:
            raise click.UsageError(
                "Option '-p/--product' is required when installing a product."
            )

        storage_backend = StorageBackend(storage)
        include_dependencies = not no_rec

        if bundle:
            service = InstallerService(
                installer_dir,
                providers=["storage"],
                storage_backend=storage_backend,
                verbose=verbose,
            )
            click.echo(
                f"Installing bundle '{bundle}' version '{version}' "
                f"from product '{product}' to '{installer_dir}'"
            )
            click.echo("Using storage provider only")
            click.echo(f"Using storage backend: {storage_backend.value}")
            if include_dependencies:
                click.echo("Loading bundle and product dependencies...")
            else:
                click.echo("Loading bundle (skipping dependencies)...")

            service.download_bundle(
                bundle,
                version,
                product,
                include_dependencies=include_dependencies,
            )
        else:
            selected_providers = list(provider) if provider else None
            service = InstallerService(
                installer_dir,
                providers=selected_providers,
                storage_backend=storage_backend,
                verbose=verbose,
            )

            click.echo(
                f"Installing product '{product}' version '{version}' to '{installer_dir}'"
            )

            if selected_providers:
                click.echo(f"Using providers: {', '.join(selected_providers)}")
            else:
                click.echo("Using all available providers: storage, github, bitbucket")
            click.echo(f"Using storage backend: {storage_backend.value}")

            if include_dependencies:
                click.echo("Loading product definitions and dependencies...")
            else:
                click.echo("Loading product definitions (skipping dependencies)...")

            service.download(
                product,
                version,
                include_dependencies=include_dependencies,
            )

        installation_table = service.get_installation_table()
        click.echo(f"\n{installation_table.get_summary()}")

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
def repair(installer_dir: str, version: str | None = None, product: str = "") -> None:
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
