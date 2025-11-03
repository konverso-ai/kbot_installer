"""Commandes CLI pour kbot-installer."""

import shutil
import subprocess
from pathlib import Path

import click

from kbot_installer.core.installable.factory import create_installable
from kbot_installer.core.installable.workarea_installable import WorkareaInstallable
from kbot_installer.core.installer_service import InstallerService
from kbot_installer.core.interactivity.database_prompter import DatabasePrompter
from kbot_installer.core.logging_config import setup_logging

# Setup logging from configuration file
setup_logging()


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
    "--interactive",
    is_flag=True,
    default=False,
    help="Interactive mode",
)
@click.option(
    "-e",
    "--env",
    type=click.Choice(["dev", "prod"], case_sensitive=False),
    default="dev",
    help="Environment type (dev or prod)",
)
@click.option(
    "-w",
    "--workarea",
    type=click.Path(),
    default=lambda: str(Path.cwd()),
    help="Workarea directory path (default: current directory)",
)
def init(
    *,
    interactive: bool = False,
    env: str = "dev",
    workarea: str,
) -> None:
    """Initialize a UV workspace and create an empty database.

    This command creates a UV workspace in the specified directory and initializes
    an empty PostgreSQL database (without schema). Products should be installed
    separately using the 'installer' command.

    \b
    Examples:
        kbot-installer init
        kbot-installer init --env prod
        kbot-installer init --interactive --env dev
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
        if not uv_executable:
            _abort_uv_not_found()

        try:
            subprocess.run(  # noqa: S603
                [uv_executable, "init"],
                cwd=workarea_path,
                check=True,
                capture_output=True,
                text=True,
            )
            click.echo("✅ UV workspace initialized successfully")
        except subprocess.CalledProcessError as e:
            _handle_uv_init_error(e)

        # Get database parameters (interactive or default)
        db_name = f"kbot_db_{env}"
        db_user = f"kbot_db_user_{env}"
        db_password = "kbot_db_pwd"  # noqa: S105  # Default password (can be changed in interactive mode)
        db_port = "5432"
        db_internal = True

        if interactive:
            prompter = DatabasePrompter()
            # Prompt for database parameters
            config = {}
            db_params = prompter.prompt_database_parameters(
                config,
                basic_installation=True,
            )
            db_name = db_params.get("db_name", db_name)
            db_user = db_params.get("db_user", db_user)
            db_password = db_params.get("db_password", db_password)
            db_port = db_params.get("db_port", db_port)
            db_internal = db_params.get("db_internal", db_internal)

        # Create WorkareaInstallable instance
        workarea_installable = WorkareaInstallable(
            name=workarea_path.name,
            target=workarea_path,
            installer_path=None,  # No installer at init stage
            db_internal=db_internal,
            db_port=db_port,
            db_name=db_name,
            db_user=db_user,
            db_password=db_password,
            prompter=DatabasePrompter() if interactive else None,
            silent_mode=not interactive,
        )

        # Setup database only (no schema)
        click.echo(f"Initializing empty database for environment: {env}")
        workarea_installable.setup_database_only(workarea_path)

        click.echo(f"✅ Workarea initialized successfully at {workarea_path}")
        click.echo(f"   Database '{db_name}' created and ready for schema loading")

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
        installable = create_installable(
            name=name,
            version=version,
            branch=branch,
            env=env,
            providers=providers,
        )

        # Ensure installer directory exists
        installer_path.mkdir(parents=True, exist_ok=True)

        # Clone product to installer directory
        click.echo(f"Cloning product '{name}' to {installer_path}")
        installable.clone(installer_path, dependencies=not no_rec)

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

        # Verify lock file was created
        lock_file = installer_path / "products.lock.json"
        if not lock_file.exists():
            click.echo(
                f"Warning: products.lock.json not found in {installer_path}",
                err=True,
            )
            click.echo("The product was cloned but lock file is missing.", err=True)
            return

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
