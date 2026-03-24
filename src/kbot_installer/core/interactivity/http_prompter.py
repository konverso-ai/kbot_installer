"""HTTP and hostname parameter prompter."""

from kbot_installer.core.interactivity.base import InteractivePrompter


class HttpPrompter(InteractivePrompter):
    """Prompter for HTTP-related parameters."""

    def prompt_http_ports(
        self,
        config: dict,
        *,
        basic_installation: bool,
        http_interface: str | None = None,
        http_port: str | None = None,
        https_port: str | None = None,
    ) -> dict:
        """Prompt and validate HTTP/HTTPS port parameters.

        Args:
            config: Configuration dictionary.
            basic_installation: If True, use basic installation mode.
            http_interface: Current http_interface value.
            http_port: Current http_port value.
            https_port: Current https_port value.

        Returns:
            Dictionary with HTTP parameters:
            - http_interface: str
            - http_port: str | None
            - https_port: str | None

        """
        result = {
            "http_interface": http_interface or config.get("http_interface") or "*",
            "http_port": http_port or config.get("http_port"),
            "https_port": https_port or config.get("https_port"),
        }

        if basic_installation:
            return result

        print(
            "By default web server accepts connections from any ('*') network interfaces."
        )
        print(
            "If you have a proxy web server behind Kbot web server you would need to accept only local connections."
        )
        print("In this case specify 'localhost' interface")
        result["http_interface"] = self.ask_input(
            f"Specify the network interface which web server should listen on [{result['http_interface']}]: ",
            result["http_interface"],
        )

        has_http = "yes" if result["http_port"] else "no"
        if self.ask_yn(f"Are you going to use HTTP port? [{has_http}]: ", has_http):
            result["http_port"] = self.ask_port(
                "Enter HTTP port number for web server in range 1024..65535",
                result["http_port"] or "8080",
                "http",
                http_port=result["http_port"],
                https_port=result["https_port"],
            )
        else:
            result["http_port"] = None

        has_https = "yes" if result["https_port"] else "no"
        if result["http_port"] is None or self.ask_yn(
            f"Are you going to use HTTPS port for secure connections? [{has_https}]: ",
            has_https,
        ):
            result["https_port"] = self.ask_port(
                "Enter HTTPS port number for web server in range 1024..65535",
                result["https_port"] or "8443",
                "https",
                http_port=result["http_port"],
                https_port=result["https_port"],
            )
        else:
            result["https_port"] = None

        return result

    def prompt_hostname(
        self,
        config: dict,
        *,
        hostname: str | None = None,
        https_port: str | None = None,
    ) -> dict:
        """Prompt and validate hostname and external URL.

        Args:
            config: Configuration dictionary.
            hostname: Current hostname value.
            https_port: HTTPS port (for determining URL scheme).

        Returns:
            Dictionary with hostname parameters:
            - hostname: str
            - kbot_external_root_url: str

        """
        result = {
            "hostname": hostname or config.get("hostname") or "",
            "kbot_external_root_url": config.get("kbot_external_root_url") or "",
        }

        # Prompt for hostname
        result["hostname"] = self._prompt_hostname_value(result["hostname"], hostname)

        # Prompt for external URL
        result["kbot_external_root_url"] = self._prompt_external_url(
            result["kbot_external_root_url"],
            result["hostname"],
            https_port,
        )

        return result

    def _prompt_hostname_value(
        self, current_hostname: str, provided_hostname: str | None
    ) -> str:
        """Prompt for hostname value.

        Args:
            current_hostname: Current hostname from config.
            provided_hostname: Hostname provided as parameter.

        Returns:
            Hostname string.

        """
        if provided_hostname:
            return provided_hostname

        if current_hostname.strip():
            return current_hostname.strip()

        return self.ask_input("Specify the current host name: ")

    def _prompt_external_url(
        self,
        current_url: str,
        hostname: str,
        https_port: str | None,
    ) -> str:
        """Prompt for external URL.

        Args:
            current_url: Current URL from config.
            hostname: Hostname value.
            https_port: HTTPS port (for determining URL scheme).

        Returns:
            External URL string.

        """
        if not current_url or current_url == "https://server.domain.com":
            # Generate default URL based on HTTPS port
            default_url = f"https://{hostname}" if https_port else f"http://{hostname}"
        else:
            default_url = current_url

        answer = self.ask_input(
            f"Specify the external URL of UI [{default_url}]: ", default_url
        )
        return answer or current_url or default_url
