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
        products: Any,
        prompter: InteractivePrompter | None = None,
        *,
        db_port: str = "5432",
        db_name: str = "kbot_db",
        db_user: str = "kbot_db_user",
        db_password: str = "kbot_db_pwd",
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
            raise RuntimeError("PG_DIR environment variable not set")

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

    def _ensure_database_running(
        self, pg_ctl: Path, pg_psql: Path, pg_data: Path
    ) -> None:
        """Ensure PostgreSQL database is running."""
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
            os.system(
                f"{pg_ctl} start -l {log_file} -D {pg_data} --silent -w -o '-p {self.db_port}'"
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
                "postgres",
                "-t",
                "-A",
                "-p",
                self.db_port,
                "-c",
                f"SELECT count(*) FROM pg_user WHERE usename = '{self.db_user}'",
            ]
        ).strip()

        if pg_user_exists.decode("utf-8") == "0":
            print(f"Creating PostgreSQL user {self.db_user}...")
            sys.stdout.flush()
            os.system(
                f"{pg_psql} postgres -q -p {self.db_port} "
                f"-c \"CREATE USER {self.db_user} PASSWORD '{self.db_password}'\""
            )
        else:
            print(f"PostgreSQL user {self.db_user} already exists.")

    def _create_database(self, pg_psql: Path) -> None:
        """Create PostgreSQL database if it doesn't exist."""
        pg_db_exists = subprocess.check_output(
            [
                str(pg_psql),
                "postgres",
                "-t",
                "-A",
                "-p",
                self.db_port,
                "-c",
                f"SELECT count(*) FROM pg_database WHERE datname = '{self.db_name}'",
            ]
        ).strip()

        if pg_db_exists.decode("utf-8") == "0":
            print(f"Creating PostgreSQL database {self.db_name}...")
            sys.stdout.flush()
            os.system(
                f"{pg_psql} postgres -q -p {self.db_port} "
                f"-c \"CREATE DATABASE {self.db_name} ENCODING 'UTF8' OWNER {self.db_user}\""
            )
            os.system(
                f"{pg_psql} -q -p {self.db_port} {self.db_name} "
                f'-c "ALTER SCHEMA public OWNER TO {self.db_user}"'
            )
            os.system(
                f"{pg_psql} -q -p {self.db_port} {self.db_name} "
                f"-c \"ALTER SYSTEM SET max_connections TO '512'\""
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
                    os.system(f"{self.pg_ctl} -D {self.target}/var/db --silent stop")
                sys.exit(1)


class ExternalDatabaseSetupManager(BaseSetupManager):
    """Manager for setting up external PostgreSQL database.

    Loads database schema from SQL files into an external database instance.
    """

    def __init__(
        self,
        target: str | Path,
        products: Any,
        prompter: InteractivePrompter | None = None,
        *,
        db_host: str = "localhost",
        db_port: str = "5432",
        db_name: str = "kbot_db",
        db_user: str = "kbot_db_user",
        db_password: str = "kbot_db_pwd",
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
            raise RuntimeError("PG_DIR environment variable not set")

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

            cmd = (
                f"export PGPASSWORD='{self.db_password}';"
                f"{pg_psql} -q -h {self.db_host} -p {self.db_port} "
                f"-d {self.db_name} -U {self.db_user} -f {sqlfile}"
            )

            if os.system(cmd) != 0:
                print("Error: can't load tables! Aborting...")
                sys.exit(1)
