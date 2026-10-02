"""Commandes CLI pour kbot-installer."""

import os
import shutil
from datetime import datetime
from pathlib import Path

import click

from database.base import DbSettings
from database.factory import build_database, create_database
from database.utils import resolve_admin_password, resolve_db_password, set_admin_password
from downloadable.factory import build_downloadable
from git.models import GitProvider
from installable.dependency_graph import DependencyGraph
from installable.factory import build_workarea
from installer_support.installer_service import InstallerService
from installer_support.kbot_commands import run_kbot_command
from installer_support.logging_config import setup_logging
from installer_support.python_requirements import install_product_python_requirements
from installer_support.thirdparty_env import prepend_thirdparty_ld_library_path, resolve_pg_dir_str
from storage.base import StorageBackendEnum
from updatable.factory import UpdatableName
from updatable.workarea_updatable import WorkareaUpdatable

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
_HOW_CHOICES = click.Choice(
    [mode.value for mode in UpdatableName],
    case_sensitive=False,
)


@click.group(
    invoke_without_command=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)
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


def _resolve_pg_dir(installer_path: Path) -> Path:
    """Resolve PG_DIR, or raise a usage error.

    Used to locate the ``psql`` client needed to apply schema/upgrade files
    (and, for an internal cluster, the ``pg_ctl``/``initdb`` binaries too),
    regardless of whether the target database is internal or external.

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


def _app_db_settings(
    *,
    db_host: str | None,
    db_port: int,
    db_user: str,
    db_password: str,
    db_name: str,
    pg_dir: Path,
) -> DbSettings:
    """Build connection settings for the kbot application database.

    Args:
        db_host: External Postgres host, or None to use the internal cluster (localhost).
        db_port: Postgres port.
        db_user: Postgres application user.
        db_password: Postgres application password.
        db_name: Postgres database name.
        pg_dir: PostgreSQL installation directory, used to locate 'psql'.

    Returns:
        The database settings, without any schema to apply.

    """
    return DbSettings(
        host=db_host or "localhost",
        port=db_port,
        database=db_name,
        user=db_user,
        password=db_password,
        psql_path=pg_dir / "bin" / "psql",
        schema_paths=[],
    )


def _resolve_backup_path(backup_file: Path, workarea_path: Path) -> Path:
    """Resolve the database backup file for 'uninstall'.

    Args:
        backup_file: File or existing directory given by the user (``~`` is
            expanded). A directory gets a timestamped 'dump_<...>.sql' file,
            named like the legacy 'dump_db.sh' does.
        workarea_path: Workarea about to be removed.

    Returns:
        The absolute path of the backup file.

    Raises:
        click.UsageError: If the backup file would be inside the workarea,
            which is removed right after.

    """
    path = backup_file.expanduser()
    if path.is_dir():
        path /= f"dump_{datetime.now().astimezone():%Y%m%d_%H%M%S}.sql"
    path = path.resolve()
    if path.is_relative_to(workarea_path.resolve()):
        msg = f"Backup file '{path}' must be outside the workarea '{workarea_path}', which is removed."
        raise click.UsageError(msg)
    return path


def _load_and_learn(
    *,
    workarea_path: Path,
    db_host: str | None,
    db_port: int,
    db_user: str,
    db_password: str,
    db_name: str,
    pg_dir: Path,
    with_load: bool,
    with_learn: bool,
    no_admin_password: bool,
) -> None:
    """Load initial data and/or train ML models after an install, via 'kbot.sh'.

    Args:
        workarea_path: Workarea directory holding 'bin/kbot.sh'.
        db_host: External Postgres host, or None to use an internal cluster.
        db_port: Postgres port.
        db_user: Postgres application user.
        db_password: Postgres application password.
        db_name: Postgres database name.
        pg_dir: PostgreSQL installation directory, used to locate 'psql'.
        with_load: Whether to load initial data and set the kbot admin password.
        with_learn: Whether to train ML models.
        no_admin_password: Whether to generate a random kbot admin password
            instead of reading 'KBOT_ADMIN_PASSWORD' (used only with `with_load`).

    """
    if with_load:
        admin_password, generated_admin_password = resolve_admin_password(no_password=no_admin_password)

        run_kbot_command(workarea_path, "load")
        set_admin_password(
            _app_db_settings(
                db_host=db_host,
                db_port=db_port,
                db_user=db_user,
                db_password=db_password,
                db_name=db_name,
                pg_dir=pg_dir,
            ),
            admin_password,
        )
        if generated_admin_password is not None:
            click.echo(f"Generated kbot admin password: {generated_admin_password}")

    if with_learn:
        run_kbot_command(workarea_path, "learn")


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
    help="Postgres password (default: 'kbot_db_pwd', unless --no-db-password is used).",
)
@click.option(
    "--db-name",
    type=str,
    default="kbot_db",
    show_default=True,
    help="Postgres database name.",
)
@click.option(
    "--no-db-password",
    is_flag=True,
    default=False,
    help=(
        "Generate a random password for the Postgres database user (--db-user), instead of "
        "--db-password or its default. Not the kbot 'admin' password (see --no-admin-password)."
    ),
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
    "--with-load",
    is_flag=True,
    default=False,
    help="Load initial data after installing (runs 'kbot.sh load').",
)
@click.option(
    "--with-learn",
    is_flag=True,
    default=False,
    help="Train ML models after installing (runs 'kbot.sh learn').",
)
@click.option(
    "--no-admin-password",
    is_flag=True,
    default=False,
    help=(
        "Generate a random kbot admin password instead of reading 'KBOT_ADMIN_PASSWORD' (used only with --with-load)."
    ),
)
@click.option(
    "-V",
    "--verbose",
    is_flag=True,
    default=False,
    help="Show detailed output (skipped products, provider download details).",
)
@click.option(
    "--force-recreate",
    is_flag=True,
    default=False,
    help="Delete an existing '--workarea-dir' before installing, instead of cancelling.",
)
def install(
    installer_dir: str,
    workarea_dir: str,
    product: str,
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
    no_db_password: bool = False,
    skip_python_requirements: bool = False,
    with_load: bool = False,
    with_learn: bool = False,
    no_admin_password: bool = False,
    verbose: bool = False,
    force_recreate: bool = False,
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
    anything is downloaded or built, unless ``--force-recreate`` is given, in
    which case the existing directory is deleted first.

    Examples:
        kbot-installer install -b ev-basic-00018 -p site-konverso --with-load --with-learn \\
            --workarea-dir ~/dev/work --installer-dir ~/dev/installer
        kbot-installer install -p site-konverso -v 2025.03-dev --with-load \\
            --workarea-dir ~/dev/work --installer-dir ~/dev/installer
        kbot-installer install -p site-konverso -v 2025.03-dev --force-recreate \\
            --workarea-dir ~/dev/work --installer-dir ~/dev/installer

    """
    if not bundle and not version:
        msg = "Option '-v/--version' is required when installing a product without '-b/--bundle'."
        raise click.UsageError(msg)

    installer_path = Path(installer_dir)
    workarea_path = Path(workarea_dir)

    if workarea_path.exists():
        if not force_recreate:
            click.echo(
                f"Workarea directory '{workarea_path}' already exists. Installation cancelled.",
                err=True,
            )
            raise click.Abort
        click.echo(f"Deleting existing workarea directory '{workarea_path}' (--force-recreate)...")
        shutil.rmtree(workarea_path)

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

        password, generated_password = resolve_db_password(db_password, no_password=no_db_password)
        schema_paths = _build_schema_paths(installer_path)

        # A 'psql' client (from the same 3rdparty PG_DIR) is required in every
        # mode to apply schema/upgrade files, even against an external database.
        pg_dir = _resolve_pg_dir(installer_path)
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

        _load_and_learn(
            workarea_path=workarea_path,
            db_host=db_host,
            db_port=db_port,
            db_user=db_user,
            db_password=password,
            db_name=db_name,
            pg_dir=pg_dir,
            with_load=with_load,
            with_learn=with_learn,
            no_admin_password=no_admin_password,
        )

        click.echo("Installation completed successfully.")

    except click.UsageError:
        raise
    except click.Abort:
        raise
    except Exception as e:
        click.echo(f"Error installing product: {e}", err=True)
        raise click.Abort from e


@cli.command(name="update")
@click.option(
    "--workarea",
    is_flag=True,
    default=False,
    help="Update the workarea.",
)
@click.option(
    "--how",
    type=_HOW_CHOICES,
    default=UpdatableName.SMOOTH.value,
    show_default=True,
    help="Update strategy to apply.",
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
    "--skip-python-requirements",
    is_flag=True,
    default=False,
    help=(
        "Skip installing each solution/customer product's requirements.txt "
        "into the 3rdparty Python (via the downloaded kbot/bin/pip3.sh)."
    ),
)
def update(
    installer_dir: str,
    workarea_dir: str,
    *,
    workarea: bool = False,
    how: str = UpdatableName.SMOOTH.value,
    skip_python_requirements: bool = False,
) -> None:
    """Update parts of an existing kbot installation.

    Currently supports ``--workarea`` to update the workarea in place, using
    the strategy given by ``--how``, then installs each solution/customer
    product's ``requirements.txt`` (unless ``--skip-python-requirements``).

    Examples:
        kbot-installer update --workarea --how repair
        kbot-installer update --workarea --how smooth -i ~/dev/installer -w ~/dev/work

    """
    if not workarea:
        msg = "Nothing to update: specify what to update (e.g. '--workarea')."
        raise click.UsageError(msg)

    try:
        installable = build_workarea(
            installer_path=Path(installer_dir),
            workarea_path=Path(workarea_dir),
        )
        installable.update_mode = True
        WorkareaUpdatable(installable=installable, mode=UpdatableName(how))()

        if not skip_python_requirements:
            install_product_python_requirements(Path(installer_dir))

        click.echo("Update completed successfully.")

    except click.UsageError:
        raise
    except Exception as e:
        click.echo(f"Error updating workarea: {e}", err=True)
        raise click.Abort from e


@cli.command(name="load")
@click.option(
    "-w",
    "--workarea-dir",
    type=click.Path(),
    default=lambda: str(Path.home() / "dev" / "work"),
    help="Workarea directory (default: $HOME/dev/work)",
)
def load(workarea_dir: str) -> None:
    """Load initial data into a workarea's database.

    Runs the installed workarea's own ``bin/kbot.sh load``.

    Examples:
        kbot-installer load -w ~/dev/work

    """
    try:
        run_kbot_command(Path(workarea_dir), "load")
        click.echo("Load completed successfully.")

    except Exception as e:
        click.echo(f"Error loading data: {e}", err=True)
        raise click.Abort from e


@cli.command(name="learn")
@click.option(
    "-w",
    "--workarea-dir",
    type=click.Path(),
    default=lambda: str(Path.home() / "dev" / "work"),
    help="Workarea directory (default: $HOME/dev/work)",
)
def learn(workarea_dir: str) -> None:
    """Train ML models for a workarea.

    Runs the installed workarea's own ``bin/kbot.sh learn``.

    Examples:
        kbot-installer learn -w ~/dev/work

    """
    try:
        run_kbot_command(Path(workarea_dir), "learn")
        click.echo("Learn completed successfully.")

    except Exception as e:
        click.echo(f"Error learning models: {e}", err=True)
        raise click.Abort from e


@cli.command(name="set-admin-password")
@click.option(
    "-i",
    "--installer-dir",
    type=click.Path(),
    default=lambda: str(Path.home() / "dev" / "installer"),
    help="Installer directory (default: $HOME/dev/installer)",
)
@click.option(
    "--db-host",
    type=str,
    default=None,
    help="Postgres hostname or IP (default: localhost, i.e. the internal database).",
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
    help="Postgres password (default: 'kbot_db_pwd').",
)
@click.option(
    "--db-name",
    type=str,
    default="kbot_db",
    show_default=True,
    help="Postgres database name.",
)
@click.option(
    "--no-admin-password",
    is_flag=True,
    default=False,
    help="Generate a random kbot admin password instead of reading 'KBOT_ADMIN_PASSWORD'.",
)
def set_admin_password_command(
    installer_dir: str,
    *,
    db_host: str | None = None,
    db_port: int = 5432,
    db_user: str = "kbot_db_user",
    db_password: str | None = None,
    db_name: str = "kbot_db",
    no_admin_password: bool = False,
) -> None:
    """Set the kbot 'admin' user's password in the database.

    Reads the password from 'KBOT_ADMIN_PASSWORD', or generates and displays a
    random one with ``--no-admin-password``. The data must already be loaded
    (see ``load``), since only the existing 'admin' user is updated.

    Examples:
        KBOT_ADMIN_PASSWORD='secret' kbot-installer set-admin-password
        kbot-installer set-admin-password --no-admin-password --db-host db.example.com

    """
    admin_password, generated_admin_password = resolve_admin_password(no_password=no_admin_password)
    password, _ = resolve_db_password(db_password, no_password=False)

    try:
        set_admin_password(
            _app_db_settings(
                db_host=db_host,
                db_port=db_port,
                db_user=db_user,
                db_password=password,
                db_name=db_name,
                pg_dir=_resolve_pg_dir(Path(installer_dir)),
            ),
            admin_password,
        )
        if generated_admin_password is not None:
            click.echo(f"Generated kbot admin password: {generated_admin_password}")
        click.echo("Admin password set successfully.")

    except click.UsageError:
        raise
    except Exception as e:
        click.echo(f"Error setting admin password: {e}", err=True)
        raise click.Abort from e


@cli.command(name="uninstall")
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
    "--db-host",
    type=str,
    default=None,
    help="Postgres hostname or IP of an external database. When unset, the internal database is removed.",
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
    help="Postgres password (default: 'kbot_db_pwd').",
)
@click.option(
    "--db-name",
    type=str,
    default="kbot_db",
    show_default=True,
    help="Postgres database name.",
)
@click.option(
    "--backup-file",
    type=click.Path(),
    default=None,
    help=(
        "Dump the database into this file before removing it (no backup when unset). "
        "A directory gets a 'dump_<YYYYmmdd_HHMMSS>.sql' file; it must be outside the workarea."
    ),
)
@click.option(
    "-y",
    "--yes",
    is_flag=True,
    default=False,
    help="Do not ask for confirmation.",
)
def uninstall(
    installer_dir: str,
    workarea_dir: str,
    *,
    db_host: str | None = None,
    db_port: int = 5432,
    db_user: str = "kbot_db_user",
    db_password: str | None = None,
    db_name: str = "kbot_db",
    backup_file: str | None = None,
    yes: bool = False,
) -> None:
    """Uninstall a kbot workarea: stop its services, then delete its database and directory.

    Mirrors the legacy 'uninstall.sh': dumps the database into
    ``--backup-file`` (only when given), runs ``bin/kbot.sh stop``,
    then deletes the database (the internal cluster under the workarea, or,
    with ``--db-host``, every object owned by ``--db-user`` in the external
    database), and finally removes the workarea directory. Nothing is removed
    if the backup fails.

    Examples:
        kbot-installer uninstall -w ~/dev/work
        kbot-installer uninstall -w ~/dev/work --backup-file ~
        kbot-installer uninstall -w ~/dev/work --backup-file ~/backups/kbot.sql
        kbot-installer uninstall -w ~/dev/work --db-host db.example.com --db-password secret -y

    """
    installer_path = Path(installer_dir)
    workarea_path = Path(workarea_dir)

    # Guard the final 'rmtree' against pointing at anything but a kbot workarea
    # ('products/' is no longer laid out from kbot 2026.01 on).
    if not (workarea_path / "products" / "kbot").is_dir() and not (workarea_path / "var" / "products.json").is_file():
        msg = f"'{workarea_path}' is not a kbot workarea directory (no 'products/kbot' nor 'var/products.json')."
        raise click.UsageError(msg)

    backup_path = None if backup_file is None else _resolve_backup_path(Path(backup_file), workarea_path)

    if db_host:
        db_description = f"all objects owned by '{db_user}' in the external database '{db_name}' on '{db_host}'"
    else:
        db_description = f"the internal database under '{workarea_path / 'var' / 'db'}'"
    click.echo(f"About to remove the workarea '{workarea_path}' entirely, including all its configuration files,")
    click.echo(f"and {db_description}.")
    if backup_path is None:
        click.echo("The database will NOT be backed up (use --backup-file to keep a dump).")
    else:
        click.echo(f"The database will first be backed up to '{backup_path}'.")
    if not yes:
        click.confirm("Continue with uninstallation?", abort=True)

    password, _ = resolve_db_password(db_password, no_password=False)
    pg_dir = _resolve_pg_dir(installer_path)
    prepend_thirdparty_ld_library_path(installer_path)

    try:
        db = create_database(
            db_host=db_host,
            db_port=db_port,
            db_user=db_user,
            password=password,
            db_name=db_name,
            workarea_path=workarea_path,
            pg_dir=pg_dir,
        )

        # Back up first, while kbot (and its database) may still be running.
        if backup_path is not None:
            click.echo(f"Backing up database to '{backup_path}'...")
            if not db.backup(backup_path):
                click.echo("Warning: no database found, nothing to back up.", err=True)

        click.echo("Stopping kbot services...")
        try:
            run_kbot_command(workarea_path, "stop")
        except (RuntimeError, OSError) as e:
            # Like 'uninstall.sh', keep going: the database is stopped explicitly below.
            click.echo(f"Warning: {e}", err=True)

        click.echo("Removing database...")
        db.destroy()

        click.echo(f"Removing workarea directory '{workarea_path}'...")
        shutil.rmtree(workarea_path)
        click.echo("Uninstallation completed successfully.")

    except Exception as e:
        click.echo(f"Error uninstalling workarea: {e}", err=True)
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
