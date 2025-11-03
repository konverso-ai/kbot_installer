"""Setup managers for database configuration."""

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from kbot_installer.core.interactivity.base import InteractivePrompter
from kbot_installer.core.setup.base import BaseSetupManager


class InternalDatabaseSetupManager(BaseSetupManager):
    """Manager for setting up internal PostgreSQL database.

    Handles PostgreSQL initialization, starting, user/database creation,
    and schema loading.
    """

    def __init__(
        self,
        target: str | Path,
        products: Any,  # noqa: ANN401
        prompter: InteractivePrompter | None = None,
        *,
        db_port: str = "5432",
        db_name: str = "kbot_db",
        db_user: str = "kbot_db_user",
        db_password: str = "kbot_db_pwd",  # noqa: S107
        update_mode: bool = False,
        silent_mode: bool = False,
    ) -> None:
        """Initialize internal database setup manager.

        Args:
            target: Target workarea directory path.
            products: Product collection.
            prompter: Optional InteractivePrompter.
            db_port: Database port number.
            db_name: Database name.
            db_user: Database user name.
            db_password: Database password.
            update_mode: Enable update/validation mode.
            silent_mode: Suppress interactive prompts.

        """
        super().__init__(
            target,
            products,
            prompter,
            update_mode=update_mode,
            silent_mode=silent_mode,
        )
        self.db_port = db_port
        self.db_name = db_name
        self.db_user = db_user
        self.db_password = db_password
        self.pg_ctl = None

    def setup(self) -> None:
        """Set up internal PostgreSQL database."""
        pg_dir = os.environ.get("PG_DIR")
        if not pg_dir:
            error_msg = "PG_DIR environment variable not set"
            raise RuntimeError(error_msg)

        pg_bin = Path(pg_dir) / "bin"
        pg_psql = pg_bin / "psql"
        pg_ctl = pg_bin / "pg_ctl"
        pg_data = self.target / "var" / "db"

        # Initialize database if needed
        if not (pg_data / "PG_VERSION").exists():
            print("\nInstalling PostgreSQL server...")
            sys.stdout.flush()
            try:
                subprocess.check_output(
                    [
                        str(pg_ctl),
                        "-D",
                        str(pg_data),
                        "-o",
                        '"-E UTF8"',
                        "-o",
                        '"--locale=en_US.utf8"',
                        "initdb",
                    ],
                    stderr=subprocess.STDOUT,
                )
            except subprocess.CalledProcessError:
                print("Cannot init database! Aborting...")
                sys.exit(1)

        # Start database if not running
        self._ensure_database_running(pg_ctl, pg_psql, pg_data)

        # Create user if needed
        self._create_database_user(pg_psql)

        # Create database if needed
        self._create_database(pg_psql)

        print("PostgreSQL is installed.")
        sys.stdout.flush()

        # Load database schema
        self._load_database_schema(pg_psql)

        sys.stdout.flush()
        self.pg_ctl = str(pg_ctl)

    def setup_database_only(self) -> None:
        """Set up internal PostgreSQL database without loading schema.

        Initializes PostgreSQL, creates user and database, but does not
        load any schema from products. Useful for initializing empty databases.
        """
        pg_dir = os.environ.get("PG_DIR")
        if not pg_dir:
            error_msg = "PG_DIR environment variable not set"
            raise RuntimeError(error_msg)

        pg_bin = Path(pg_dir) / "bin"
        pg_psql = pg_bin / "psql"
        pg_ctl = pg_bin / "pg_ctl"
        pg_data = self.target / "var" / "db"

        # Initialize database if needed
        if not (pg_data / "PG_VERSION").exists():
            print("\nInstalling PostgreSQL server...")
            sys.stdout.flush()
            try:
                subprocess.check_output(
                    [
                        str(pg_ctl),
                        "-D",
                        str(pg_data),
                        "-o",
                        '"-E UTF8"',
                        "-o",
                        '"--locale=en_US.utf8"',
                        "initdb",
                    ],
                    stderr=subprocess.STDOUT,
                )
            except subprocess.CalledProcessError:
                print("Cannot init database! Aborting...")
                sys.exit(1)

        # Start database if not running
        self._ensure_database_running(pg_ctl, pg_psql, pg_data)

        # Create user if needed
        self._create_database_user(pg_psql)

        # Create database if needed
        self._create_database(pg_psql)

        print("PostgreSQL is installed (database only, no schema loaded).")
        sys.stdout.flush()
        self.pg_ctl = str(pg_ctl)

    def _ensure_database_running(
        self,
        pg_ctl: Path,
        pg_psql: Path,
        pg_data: Path,
    ) -> None:
        """Ensure PostgreSQL database is running."""
        _ = pg_psql  # unused but kept for API consistency
        # Check if database is running
        try:
            subprocess.check_output(
                [str(pg_ctl), "status", "--silent", "-D", str(pg_data)],
                stderr=subprocess.STDOUT,
            )
        except subprocess.CalledProcessError:
            # Database is not up, try to start it
            print("Starting PostgreSQL server...")
            sys.stdout.flush()
            log_file = self.target / "logs" / "postgres.log"
            # Use workarea var/run for Unix sockets to avoid permission issues
            socket_dir = self.target / "var" / "run"
            socket_dir.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                [
                    str(pg_ctl),
                    "start",
                    "-l",
                    str(log_file),
                    "-D",
                    str(pg_data),
                    "--silent",
                    "-w",
                    "-o",
                    f"-p{self.db_port}",
                    "-o",
                    f"-k{socket_dir}",
                ],
                check=False,
            )

            # Verify database started
            try:
                subprocess.check_output(
                    [str(pg_ctl), "status", "--silent", "-D", str(pg_data)],
                    stderr=subprocess.STDOUT,
                )
            except subprocess.CalledProcessError:
                print("Error: can't start PostgreSQL server! Aborting...")
                sys.exit(1)

    def _create_database_user(self, pg_psql: Path) -> None:
        """Create PostgreSQL user if it doesn't exist."""
        pg_user_exists = subprocess.check_output(
            [
                str(pg_psql),
                "-h",
                "localhost",
                "postgres",
                "-t",
                "-A",
                "-p",
                self.db_port,
                "-c",
                f"SELECT count(*) FROM pg_user WHERE usename = '{self.db_user}'",  # noqa: S608
            ]
        ).strip()

        if pg_user_exists.decode("utf-8") == "0":
            print(f"Creating PostgreSQL user {self.db_user}...")
            sys.stdout.flush()
            # Use environment variable for password to avoid command injection
            env = os.environ.copy()
            # Note: SQL injection is handled separately (noqa: S608)
            # The password is passed via environment variable, not command line
            subprocess.run(
                [
                    str(pg_psql),
                    "-h",
                    "localhost",
                    "postgres",
                    "-q",
                    "-p",
                    self.db_port,
                    "-c",
                    f"CREATE USER {self.db_user} PASSWORD '{self.db_password}'",
                ],
                env=env,
                check=False,
            )
        else:
            print(f"PostgreSQL user {self.db_user} already exists.")

    def _create_database(self, pg_psql: Path) -> None:
        """Create PostgreSQL database if it doesn't exist."""
        pg_db_exists = subprocess.check_output(
            [
                str(pg_psql),
                "-h",
                "localhost",
                "postgres",
                "-t",
                "-A",
                "-p",
                self.db_port,
                "-c",
                f"SELECT count(*) FROM pg_database WHERE datname = '{self.db_name}'",  # noqa: S608
            ]
        ).strip()

        if pg_db_exists.decode("utf-8") == "0":
            print(f"Creating PostgreSQL database {self.db_name}...")
            sys.stdout.flush()
            # Note: SQL injection is handled separately (noqa: S608)
            # Database names, user names are validated or controlled
            subprocess.run(
                [
                    str(pg_psql),
                    "-h",
                    "localhost",
                    "postgres",
                    "-q",
                    "-p",
                    self.db_port,
                    "-c",
                    f"CREATE DATABASE {self.db_name} ENCODING 'UTF8' OWNER {self.db_user}",
                ],
                check=False,
            )
            subprocess.run(
                [
                    str(pg_psql),
                    "-h",
                    "localhost",
                    "-q",
                    "-p",
                    self.db_port,
                    self.db_name,
                    "-c",
                    f"ALTER SCHEMA public OWNER TO {self.db_user}",
                ],
                check=False,
            )
            subprocess.run(
                [
                    str(pg_psql),
                    "-h",
                    "localhost",
                    "-q",
                    "-p",
                    self.db_port,
                    self.db_name,
                    "-c",
                    "ALTER SYSTEM SET max_connections TO '512'",
                ],
                check=False,
            )
        else:
            print(f"PostgreSQL database {self.db_name} already exists.")

    def _load_database_schema(self, pg_psql: Path) -> None:
        """Load database schema from SQL files in products."""
        print("Loading database tables...")
        # Convert to list if it's iterable but not a list
        products_list = (
            list(self.products)
            if not isinstance(self.products, list)
            else self.products
        )
        for product in reversed(products_list):
            if not hasattr(product, "name") or not hasattr(product, "dirname"):
                continue

            sqlfile = (
                self.target
                / "products"
                / product.name
                / "db"
                / "init"
                / "db_schema.sql"
            )
            if not sqlfile.exists():
                continue

            if (
                subprocess.run(
                    [
                        str(pg_psql),
                        "-h",
                        "localhost",
                        "-q",
                        "-v",
                        "ON_ERROR_STOP=1",
                        "-p",
                        self.db_port,
                        self.db_name,
                        "-U",
                        self.db_user,
                        "-f",
                        str(sqlfile),
                    ],
                    check=False,
                ).returncode
                != 0
            ):
                print("Error: can't init DB schema! Aborting...")
                if self.pg_ctl:
                    pg_data_path = self.target / "var" / "db"
                    subprocess.run(
                        [
                            str(self.pg_ctl),
                            "-D",
                            str(pg_data_path),
                            "--silent",
                            "stop",
                        ],
                        check=False,
                    )
                sys.exit(1)


class ExternalDatabaseSetupManager(BaseSetupManager):
    """Manager for setting up external PostgreSQL database.

    Loads database schema from SQL files into an external database instance.
    """

    def __init__(
        self,
        target: str | Path,
        products: Any,  # noqa: ANN401
        prompter: InteractivePrompter | None = None,
        *,
        db_host: str = "localhost",
        db_port: str = "5432",
        db_name: str = "kbot_db",
        db_user: str = "kbot_db_user",
        db_password: str = "kbot_db_pwd",  # noqa: S107
        update_mode: bool = False,
        silent_mode: bool = False,
    ) -> None:
        """Initialize external database setup manager.

        Args:
            target: Target workarea directory path.
            products: Product collection.
            prompter: Optional InteractivePrompter.
            db_host: Database hostname.
            db_port: Database port number.
            db_name: Database name.
            db_user: Database user name.
            db_password: Database password.
            update_mode: Enable update/validation mode.
            silent_mode: Suppress interactive prompts.

        """
        super().__init__(
            target,
            products,
            prompter,
            update_mode=update_mode,
            silent_mode=silent_mode,
        )
        self.db_host = db_host
        self.db_port = db_port
        self.db_name = db_name
        self.db_user = db_user
        self.db_password = db_password

    def setup(self) -> None:
        """Load database schema into external database."""
        pg_dir = os.environ.get("PG_DIR")
        if not pg_dir:
            error_msg = "PG_DIR environment variable not set"
            raise RuntimeError(error_msg)

        pg_bin = Path(pg_dir) / "bin"
        pg_psql = pg_bin / "psql"

        # Load database schema definition
        print("Loading tables to external database...")
        sys.stdout.flush()

        # Convert to list if it's iterable but not a list
        products_list = (
            list(self.products)
            if not isinstance(self.products, list)
            else self.products
        )
        for product in reversed(products_list):
            if not hasattr(product, "name") or not hasattr(product, "dirname"):
                continue

            sqlfile = (
                self.target
                / "products"
                / product.name
                / "db"
                / "init"
                / "db_schema.sql"
            )
            if not sqlfile.exists():
                continue

            # Use environment variable for password to avoid command injection
            env = os.environ.copy()
            env["PGPASSWORD"] = self.db_password

            result = subprocess.run(
                [
                    str(pg_psql),
                    "-q",
                    "-h",
                    self.db_host,
                    "-p",
                    self.db_port,
                    "-d",
                    self.db_name,
                    "-U",
                    self.db_user,
                    "-f",
                    str(sqlfile),
                ],
                env=env,
                check=False,
            )

            if result.returncode != 0:
                print("Error: can't load tables! Aborting...")
                sys.exit(1)

    def setup_database_only(self) -> None:  # noqa: PLR0912, PLR0915
        """Set up external PostgreSQL database without loading schema.

        Verifies connection, creates user and database if they don't exist,
        but does not load any schema from products. Useful for initializing
        empty databases on external PostgreSQL instances.

        Note: Creating user and database requires superuser privileges.
        If the user doesn't have these privileges, they should create the
        database and user manually before running this command.
        """
        pg_dir = os.environ.get("PG_DIR")
        if not pg_dir:
            error_msg = "PG_DIR environment variable not set"
            raise RuntimeError(error_msg)

        pg_bin = Path(pg_dir) / "bin"
        pg_psql = pg_bin / "psql"

        # Use environment variable for password to avoid command injection
        env = os.environ.copy()
        env["PGPASSWORD"] = self.db_password

        # First, try to connect to the target database
        # If it doesn't exist, we'll try to create it as superuser
        print("Verifying connection to external PostgreSQL server...")
        sys.stdout.flush()

        # Test connection to target database first
        test_result = subprocess.run(
            [
                str(pg_psql),
                "-h",
                self.db_host,
                "-p",
                self.db_port,
                "-d",
                self.db_name,
                "-U",
                self.db_user,
                "-c",
                "SELECT 1",
            ],
            env=env,
            capture_output=True,
            check=False,
        )

        # If connection to target DB fails, try to create DB as superuser
        # First try with 'postgres' user (common default superuser)
        # Note: This requires knowing the postgres user password
        can_create = False
        superuser = None
        superuser_password = None

        if test_result.returncode != 0:
            # Try connecting as postgres user (using same password or empty)
            # In practice, the user should have created DB/user manually or
            # provided superuser credentials
            for su_user in ["postgres", self.db_user]:
                test_superuser = subprocess.run(
                    [
                        str(pg_psql),
                        "-h",
                        self.db_host,
                        "-p",
                        self.db_port,
                        "-d",
                        "postgres",
                        "-U",
                        su_user,
                        "-c",
                        "SELECT 1",
                    ],
                    env=env,
                    capture_output=True,
                    check=False,
                )
                if test_superuser.returncode == 0:
                    can_create = True
                    superuser = su_user
                    superuser_password = self.db_password
                    break

        if test_result.returncode == 0:
            # Database connection successful
            print(
                f"External PostgreSQL database '{self.db_name}' is ready (no schema loaded)."
            )
            sys.stdout.flush()
            return

        if not can_create:
            print(
                "Warning: Could not connect to PostgreSQL server as superuser.",
            )
            print("Database and user should be created manually if they don't exist.")
            print(f"Attempting to verify connection to '{self.db_name}'...")
            sys.stdout.flush()
        else:
            # Create user if it doesn't exist
            env["PGPASSWORD"] = superuser_password
            user_exists = subprocess.run(
                [
                    str(pg_psql),
                    "-h",
                    self.db_host,
                    "-p",
                    self.db_port,
                    "-d",
                    "postgres",
                    "-U",
                    superuser,
                    "-t",
                    "-A",
                    "-c",
                    f"SELECT count(*) FROM pg_user WHERE usename = '{self.db_user}'",  # noqa: S608
                ],
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )

            if user_exists.returncode == 0 and user_exists.stdout.strip() == "0":
                print(f"Creating PostgreSQL user {self.db_user}...")
                sys.stdout.flush()
                subprocess.run(
                    [
                        str(pg_psql),
                        "-h",
                        self.db_host,
                        "-p",
                        self.db_port,
                        "-d",
                        "postgres",
                        "-U",
                        superuser,
                        "-q",
                        "-c",
                        f"CREATE USER {self.db_user} PASSWORD '{self.db_password}'",
                    ],
                    env=env,
                    check=False,
                )
            else:
                print(
                    f"PostgreSQL user {self.db_user} already exists or cannot be checked."
                )
                sys.stdout.flush()

            # Create database if it doesn't exist
            db_exists = subprocess.run(
                [
                    str(pg_psql),
                    "-h",
                    self.db_host,
                    "-p",
                    self.db_port,
                    "-d",
                    "postgres",
                    "-U",
                    superuser,
                    "-t",
                    "-A",
                    "-c",
                    f"SELECT count(*) FROM pg_database WHERE datname = '{self.db_name}'",  # noqa: S608
                ],
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )

            if db_exists.returncode == 0 and db_exists.stdout.strip() == "0":
                print(f"Creating PostgreSQL database {self.db_name}...")
                sys.stdout.flush()
                subprocess.run(
                    [
                        str(pg_psql),
                        "-h",
                        self.db_host,
                        "-p",
                        self.db_port,
                        "-d",
                        "postgres",
                        "-U",
                        superuser,
                        "-q",
                        "-c",
                        f"CREATE DATABASE {self.db_name} ENCODING 'UTF8' OWNER {self.db_user}",
                    ],
                    env=env,
                    check=False,
                )
                # Set schema owner
                env["PGPASSWORD"] = self.db_password
                subprocess.run(
                    [
                        str(pg_psql),
                        "-h",
                        self.db_host,
                        "-p",
                        self.db_port,
                        "-d",
                        self.db_name,
                        "-U",
                        self.db_user,
                        "-q",
                        "-c",
                        f"ALTER SCHEMA public OWNER TO {self.db_user}",
                    ],
                    env=env,
                    check=False,
                )
            else:
                print(
                    f"PostgreSQL database {self.db_name} already exists or cannot be checked."
                )
                sys.stdout.flush()

        # Verify final connection to the target database
        env["PGPASSWORD"] = self.db_password
        final_test = subprocess.run(
            [
                str(pg_psql),
                "-h",
                self.db_host,
                "-p",
                self.db_port,
                "-d",
                self.db_name,
                "-U",
                self.db_user,
                "-c",
                "SELECT 1",
            ],
            env=env,
            capture_output=True,
            check=False,
        )

        if final_test.returncode == 0:
            print(
                f"External PostgreSQL database '{self.db_name}' is ready (no schema loaded)."
            )
            sys.stdout.flush()
        else:
            print(
                f"Warning: Could not verify connection to database '{self.db_name}'.",
            )
            print(
                "Please ensure the database and user exist and credentials are correct."
            )
            sys.stdout.flush()
