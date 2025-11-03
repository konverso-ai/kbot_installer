"""Database parameter prompter."""

import os
import re
import socket
import subprocess
from pathlib import Path

from kbot_installer.core.interactivity.base import InteractivePrompter


class DatabasePrompter(InteractivePrompter):
    """Prompter for database-related parameters."""

    # Constants for validation
    MAX_HOSTNAME_LENGTH = 255
    MIN_PORT = 1
    MAX_PORT = 65535
    MAX_IDENTIFIER_LENGTH = 63  # PostgreSQL identifier limit

    def _validate_db_host(self, host: str) -> str:
        """Validate and sanitize database hostname.

        Args:
            host: Hostname to validate.

        Returns:
            Validated hostname.

        Raises:
            ValueError: If hostname is invalid or contains dangerous characters.

        """
        # Strip whitespace first
        host = host.strip()
        # Allow alphanumeric, dots, hyphens, underscores, and colons (for IPv6)
        if not re.match(r"^[a-zA-Z0-9._:-]+$", host):
            msg = f"Invalid hostname: {host}. Only alphanumeric, dots, hyphens, underscores, and colons are allowed."
            raise ValueError(msg)
        # Limit length to prevent buffer overflow
        if len(host) > self.MAX_HOSTNAME_LENGTH:
            msg = f"Hostname too long (max {self.MAX_HOSTNAME_LENGTH} characters)."
            raise ValueError(msg)
        return host

    def _validate_db_port(self, port: str) -> str:
        """Validate and sanitize database port number.

        Args:
            port: Port number to validate.

        Returns:
            Validated port number.

        Raises:
            ValueError: If port is invalid.

        """
        # Port must be numeric and within valid range
        if not port.isdigit():
            msg = f"Invalid port: {port}. Port must be numeric."
            raise ValueError(msg)
        port_num = int(port)
        if port_num < self.MIN_PORT or port_num > self.MAX_PORT:
            msg = f"Invalid port: {port}. Port must be between {self.MIN_PORT} and {self.MAX_PORT}."
            raise ValueError(msg)
        return port

    def _validate_db_identifier(self, identifier: str, name: str) -> str:
        """Validate and sanitize database name or username.

        Args:
            identifier: Database name or username to validate.
            name: Type of identifier ('database name' or 'username').

        Returns:
            Validated identifier.

        Raises:
            ValueError: If identifier is invalid or contains dangerous characters.

        """
        # Strip whitespace first
        identifier = identifier.strip()
        # PostgreSQL identifiers: alphanumeric, underscore, dollar sign, but for safety
        # we'll be more restrictive and disallow dollar sign
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", identifier):
            msg = (
                f"Invalid {name}: {identifier}. "
                "Must start with letter or underscore and contain only alphanumeric characters and underscores."
            )
            raise ValueError(msg)
        # Limit length (PostgreSQL limit is 63 bytes)
        if len(identifier) > self.MAX_IDENTIFIER_LENGTH:
            msg = f"{name.capitalize()} too long (max {self.MAX_IDENTIFIER_LENGTH} characters)."
            raise ValueError(msg)
        return identifier

    def _test_external_database_connection(self, result: dict[str, str | bool]) -> bool:
        """Test connection to external database with validated parameters.

        Args:
            result: Dictionary with database parameters.

        Returns:
            True if connection successful, False otherwise.

        """
        pg_dir = Path(os.environ["PG_DIR"])
        # Resolve to absolute path to avoid security risks with partial paths
        pg_psql = (pg_dir / "bin" / "psql").resolve()

        if not pg_psql.exists():
            print(
                f"Error: psql executable not found at {pg_psql}. "
                "Please check PG_DIR environment variable."
            )
            return False

        # Validate all user inputs before passing to subprocess
        # This prevents command injection even though we use a list of arguments
        try:
            validated_host = self._validate_db_host(result["db_host"])
            validated_port = self._validate_db_port(result["db_port"])
            validated_db_name = self._validate_db_identifier(
                result["db_name"], "database name"
            )
            validated_db_user = self._validate_db_identifier(
                result["db_user"], "username"
            )
        except ValueError as e:
            print(f"Validation error: {e}")
            return False

        # Use environment variable for password to avoid command injection
        env = os.environ.copy()
        env["PGPASSWORD"] = result["db_password"]

        # Use subprocess.run() with list of arguments for security
        # All user inputs are validated and sanitized above
        # Redirect stdout/stderr to /dev/null for silent test
        result_process = subprocess.run(
            [
                str(pg_psql),
                "-h",
                validated_host,
                "-p",
                validated_port,
                "-d",
                validated_db_name,
                "-U",
                validated_db_user,
                "-c",
                "select 1",
            ],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )

        return result_process.returncode == 0

    def prompt_database_parameters(
        self,
        config: dict,
        *,
        basic_installation: bool,
        db_internal: bool | None = None,
        db_host: str | None = None,
        db_port: str | None = None,
        db_name: str | None = None,
        db_user: str | None = None,
        db_password: str | None = None,
    ) -> dict:
        """Prompt and validate database parameters.

        Args:
            config: Configuration dictionary (for reading defaults).
            basic_installation: If True, use basic installation mode.
            db_internal: Current db_internal value.
            db_host: Current db_host value.
            db_port: Current db_port value.
            db_name: Current db_name value.
            db_user: Current db_user value.
            db_password: Current db_password value.

        Returns:
            Dictionary with database parameters:
            - db_internal: bool
            - db_host: str
            - db_port: str
            - db_name: str
            - db_user: str
            - db_password: str

        """
        result = {
            "db_internal": db_internal,
            "db_host": db_host or config.get("db_host") or "localhost",
            "db_port": db_port or config.get("db_port") or "5432",
            "db_name": db_name or config.get("db_name") or "kbot_db",
            "db_user": db_user or config.get("db_user") or "kbot_db_user",
            "db_password": db_password or config.get("db_password") or "kbot_db_pwd",
        }

        if basic_installation:
            # Basic installation always uses internal database
            result["db_internal"] = True
            return result

        # Advanced installation: ask if internal or external
        db_internal_str = "yes" if result["db_internal"] else "no"
        result["db_internal"] = self.ask_yn(
            f"Install own Kbot database engine? [{db_internal_str}]: ",
            db_internal_str,
        )

        while True:
            # Hostname for external database
            if not result["db_internal"]:
                result["db_host"] = self.ask_input(
                    f"Enter a hostname where external database is located [{result['db_host']}]: ",
                    result["db_host"],
                )

            # Database port
            while True:
                result["db_port"] = self.ask_port(
                    "Specify the database port number",
                    result["db_port"],
                    "db",
                    limit=True,
                )
                if result["db_internal"]:
                    # Check if DB port is in use
                    if self._port_in_use(result["db_port"]):
                        print(
                            f"Port {result['db_port']} already in use now, please specify another port."
                        )
                    else:
                        break
                else:
                    break

            result["db_name"] = self.ask_input(
                f"Enter a database name [{result['db_name']}]: ",
                result["db_name"],
            )
            result["db_user"] = self.ask_input(
                f"Enter a database user name [{result['db_user']}]: ",
                result["db_user"],
            )
            result["db_password"] = self.ask_input(
                f"Enter a password for database user [{result['db_password']}]: ",
                result["db_password"],
            )

            if not result["db_internal"]:
                # Test connection to external database
                if self._test_external_database_connection(result):
                    break
                print(
                    "Can't connect to an external database with specified parameters!"
                )
            else:
                break

        return result

    def prompt_pgbouncer_parameters(
        self,
        config: dict,
        *,
        basic_installation: bool,
        pgbouncer_port: str | None = None,
    ) -> dict:
        """Prompt and validate pgbouncer parameters.

        Args:
            config: Configuration dictionary.
            basic_installation: If True, use basic installation mode.
            pgbouncer_port: Current pgbouncer_port value.

        Returns:
            Dictionary with pgbouncer parameters:
            - use_pgbouncer: bool
            - pgbouncer_port: str | None

        """
        result = {
            "use_pgbouncer": False,
            "pgbouncer_port": pgbouncer_port or config.get("pgbouncer_port") or "6432",
        }

        if basic_installation:
            return result

        result["use_pgbouncer"] = self.ask_yn("Use pgbouncer? [no]: ", "no")
        if result["use_pgbouncer"]:
            result["pgbouncer_port"] = self.ask_port(
                "Specify the pgbouncer port number",
                result["pgbouncer_port"],
                "db",
            )

        return result

    def _port_in_use(self, port: str) -> bool:
        """Check if a port is in use.

        Args:
            port: Port number to check.

        Returns:
            True if port is in use.

        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        res = sock.connect_ex(("127.0.0.1", int(port)))
        sock.close()
        return res == 0
