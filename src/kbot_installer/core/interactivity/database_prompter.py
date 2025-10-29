"""Database parameter prompter."""

import os
import socket
from pathlib import Path

from kbot_installer.core.interactivity.base import InteractivePrompter


class DatabasePrompter(InteractivePrompter):
    """Prompter for database-related parameters."""

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
                pg_dir = Path(os.environ["PG_DIR"])
                pg_psql = pg_dir / "bin" / "psql"
                # Note: Using subprocess would be safer but keeping os.system for compatibility
                test_cmd = (
                    f"export PGPASSWORD='{result['db_password']}';"
                    f"{pg_psql} -h {result['db_host']} -p {result['db_port']} "
                    f"-d {result['db_name']} -U {result['db_user']} -c 'select 1' > /dev/null"
                )
                if os.system(test_cmd) == 0:  # noqa: S605
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
