"""Redis parameter prompter."""

import socket
from pathlib import Path

from kbot_installer.core.interactivity.base import InteractivePrompter


class RedisPrompter(InteractivePrompter):
    """Prompter for Redis-related parameters."""

    def prompt_redis_parameters(
        self,
        config: dict,
        *,
        basic_installation: bool,
        cachedir: str | Path | None = None,
        redis_internal: bool | None = None,
        redis_host: str | None = None,
        redis_port: str | None = None,
        redis_tls_port: str | None = None,
        redis_db_number: str | None = None,
        redis_pwd: str | None = None,
        redis_tls_cert_file: str | None = None,
        redis_tls_key_file: str | None = None,
        redis_tls_ca_cert_file: str | None = None,
    ) -> dict:
        """Prompt and validate Redis parameters.

        Args:
            config: Configuration dictionary.
            basic_installation: If True, use basic installation mode.
            cachedir: Cache directory path.
            redis_internal: Current redis_internal value.
            redis_host: Current redis_host value.
            redis_port: Current redis_port value.
            redis_tls_port: Current redis_tls_port value.
            redis_db_number: Current redis_db_number value.
            redis_pwd: Current redis_pwd value.
            redis_tls_cert_file: Current redis_tls_cert_file value.
            redis_tls_key_file: Current redis_tls_key_file value.
            redis_tls_ca_cert_file: Current redis_tls_ca_cert_file value.

        Returns:
            Dictionary with Redis parameters.

        """
        result = {
            "redis_internal": redis_internal or config.get("redis_internal", True),
            "redis_host": redis_host or config.get("redis_host"),
            "redis_port": redis_port or config.get("redis_port"),
            "redis_tls_port": redis_tls_port or config.get("redis_tls_port"),
            "redis_db_number": redis_db_number or config.get("redis_db_number"),
            "redis_pwd": redis_pwd or config.get("redis_pwd"),
            "redis_tls_cert_file": redis_tls_cert_file
            or config.get("redis_tls_cert_file"),
            "redis_tls_key_file": redis_tls_key_file
            or config.get("redis_tls_key_file"),
            "redis_tls_ca_cert_file": redis_tls_ca_cert_file
            or config.get("redis_tls_ca_cert_file"),
        }

        if basic_installation:
            # Basic installation: create redis cache directory
            if cachedir:
                cachedir_path = Path(cachedir)
                redis_cache = cachedir_path / "redis"
                result["redis_cache_dir"] = str(redis_cache)
            return result

        # Advanced installation: ask if internal or external Redis
        redis_internal_str = "yes" if result["redis_internal"] else "no"
        result["redis_internal"] = self.ask_yn(
            f"Install own Kbot Redis engine? [{redis_internal_str}]: ",
            redis_internal_str,
        )

        if result["redis_internal"]:
            if cachedir:
                cachedir_path = Path(cachedir)
                redis_cache = cachedir_path / "redis"
                result["redis_cache_dir"] = str(redis_cache)
        else:
            # External Redis: ask for hostname and database number
            result["redis_host"] = self.ask_input(
                f"Enter a hostname where external Redis is located [{result['redis_host']}]: ",
                result["redis_host"] or "",
            )

            result["redis_db_number"] = self.ask_input(
                f"Enter a database number [{result['redis_db_number']}]: ",
                result["redis_db_number"] or "",
            )

            # Redis password
            redis_auth = "yes" if result["redis_pwd"] else "no"
            redis_secured = self.ask_yn(
                f"Is your redis db is secured with a password? [{redis_auth}]: ",
                redis_auth,
            )
            if redis_secured:
                result["redis_pwd"] = self.prompt_redis_password()

            # Redis TLS
            redis_tls = "yes" if result["redis_tls_port"] else "no"
            if self.ask_yn(f"Use redis db with TLS? [{redis_tls}]: ", redis_tls):
                while True:
                    result["redis_tls_port"] = self.ask_port(
                        "Specify the Redis port number",
                        result["redis_tls_port"] or result["redis_port"] or "6379",
                        "redis",
                    )
                    # Check if port is in use (for internal installations)
                    if not self._port_in_use(result["redis_tls_port"]):
                        result["redis_port"] = "0"
                        break
                    print(
                        f"Port {result['redis_tls_port']} already in use now, please specify another port."
                    )

                # TLS certificates
                redis_tls_files = (
                    "no"
                    if (
                        result["redis_tls_cert_file"]
                        and result["redis_tls_key_file"]
                        and result["redis_tls_ca_cert_file"]
                    )
                    else "yes"
                )
                if self.ask_yn(
                    f"Generate redis SSL files? [{redis_tls_files}]: ",
                    redis_tls_files,
                ):
                    # Will be handled by caller (generates certificates)
                    result["generate_ssl"] = True
                else:
                    result["redis_tls_cert_file"] = self.ask_input(
                        f"Enter full path to redis certificate file [{result['redis_tls_cert_file']}]: ",
                        result["redis_tls_cert_file"] or "",
                    )
                    result["redis_tls_key_file"] = self.ask_input(
                        f"Enter full path to redis key file [{result['redis_tls_key_file']}]: ",
                        result["redis_tls_key_file"] or "",
                    )
                    result["redis_tls_ca_cert_file"] = self.ask_input(
                        f"Enter full path to redis Certificate Authority file [{result['redis_tls_ca_cert_file']}]: ",
                        result["redis_tls_ca_cert_file"] or "",
                    )

        return result

    def prompt_redis_password(self) -> str:
        """Prompt for Redis password.

        Returns:
            Redis password.

        """
        return self.ask_password("Enter password for the default 'Redis' user: ")

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
