"""Tests for HttpPrompter class."""

from collections.abc import Iterator
from unittest.mock import Mock, patch

import pytest

from kbot_installer.core.interactivity.http_prompter import HttpPrompter


@pytest.fixture(autouse=True)
def mock_print() -> Iterator[None]:
    """Fixture to automatically mock print to prevent memory accumulation."""

    # Use a simple function that does nothing - no storage, no accumulation
    def _noop(*args: object, **kwargs: object) -> None:
        """No-op function that discards all arguments immediately."""

    with patch("builtins.print", _noop):
        yield


class TestHttpPrompterPromptHttpPorts:
    """Test cases for HttpPrompter.prompt_http_ports."""

    def test_prompt_http_ports_basic_installation(self) -> None:
        """Test prompt_http_ports with basic installation."""
        prompter = HttpPrompter()
        config = {"http_interface": "localhost", "http_port": "8080"}
        result = prompter.prompt_http_ports(config, basic_installation=True)
        assert result["http_interface"] == "localhost"
        assert result["http_port"] == "8080"

    @patch("builtins.input", side_effect=["localhost", "n", ""])
    def test_prompt_http_ports_interface_prompt(self, mock_input: Mock) -> None:
        """Test prompt_http_ports prompts for interface."""
        prompter = HttpPrompter()
        config = {"http_interface": "*"}
        result = prompter.prompt_http_ports(config, basic_installation=False)
        # When http_port is None, HTTPS is always prompted (line 68)
        # Empty input for ask_port will use default "8443"
        assert result["http_interface"] == "localhost"
        assert result["http_port"] is None
        assert result["https_port"] == "8443"

    @patch("builtins.input", side_effect=["localhost", "y", "8080", "n"])
    def test_prompt_http_ports_http_only(self, mock_input: Mock) -> None:
        """Test prompt_http_ports with HTTP only."""
        prompter = HttpPrompter()
        config = {"http_interface": "*"}
        result = prompter.prompt_http_ports(config, basic_installation=False)
        assert result["http_port"] == "8080"
        assert result["https_port"] is None

    @patch("builtins.input", side_effect=["localhost", "n", "y", "8443"])
    def test_prompt_http_ports_https_only(self, mock_input: Mock) -> None:
        """Test prompt_http_ports with HTTPS only."""
        prompter = HttpPrompter()
        config = {"http_interface": "*"}
        result = prompter.prompt_http_ports(config, basic_installation=False)
        assert result["http_port"] is None
        assert result["https_port"] == "8443"

    @patch("builtins.input", side_effect=["localhost", "y", "8080", "y", "8443"])
    def test_prompt_http_ports_both(self, mock_input: Mock) -> None:
        """Test prompt_http_ports with both HTTP and HTTPS."""
        prompter = HttpPrompter()
        config = {"http_interface": "*"}
        result = prompter.prompt_http_ports(config, basic_installation=False)
        assert result["http_port"] == "8080"
        assert result["https_port"] == "8443"

    @patch("builtins.input", side_effect=["*", "", "", "", ""])
    def test_prompt_http_ports_uses_config_defaults(self, mock_input: Mock) -> None:
        """Test prompt_http_ports uses config defaults."""
        prompter = HttpPrompter()
        config = {"http_interface": "*", "http_port": "8080", "https_port": "8443"}
        result = prompter.prompt_http_ports(config, basic_installation=False)
        # When defaults exist:
        # - ask_input("*") returns "*" for interface
        # - ask_yn("", "yes") returns True (empty becomes "yes")
        # - ask_port("", "8080") returns "8080" (empty uses default)
        # - ask_yn("", "yes") returns True
        # - ask_port("", "8443") returns "8443" (empty uses default)
        assert result["http_interface"] == "*"
        assert result["http_port"] == "8080"
        assert result["https_port"] == "8443"


class TestHttpPrompterPromptHostname:
    """Test cases for HttpPrompter.prompt_hostname."""

    @patch("builtins.input", return_value="")
    def test_prompt_hostname_with_provided_hostname(self, mock_input: Mock) -> None:
        """Test prompt_hostname with provided hostname."""
        prompter = HttpPrompter()
        config = {}
        result = prompter.prompt_hostname(config, hostname="example.com")
        assert result["hostname"] == "example.com"
        # Should use default URL since kbot_external_root_url is not in config
        assert result["kbot_external_root_url"] == "http://example.com"

    @patch("builtins.input", return_value="example.com")
    def test_prompt_hostname_from_config(self, mock_input: Mock) -> None:
        """Test prompt_hostname uses config hostname."""
        prompter = HttpPrompter()
        config = {"hostname": "config.example.com"}
        result = prompter.prompt_hostname(config)
        assert result["hostname"] == "config.example.com"

    @patch("builtins.input", return_value="example.com")
    def test_prompt_hostname_no_config(self, mock_input: Mock) -> None:
        """Test prompt_hostname prompts when no config."""
        prompter = HttpPrompter()
        config = {}
        result = prompter.prompt_hostname(config)
        assert result["hostname"] == "example.com"

    @patch("builtins.input", return_value="https://external.example.com")
    def test_prompt_hostname_external_url(self, mock_input: Mock) -> None:
        """Test prompt_hostname prompts for external URL."""
        prompter = HttpPrompter()
        config = {"hostname": "example.com", "kbot_external_root_url": ""}
        result = prompter.prompt_hostname(config, https_port="8443")
        assert "kbot_external_root_url" in result

    @patch("builtins.input", return_value="")
    def test_prompt_hostname_external_url_default_https(self, mock_input: Mock) -> None:
        """Test prompt_hostname generates default URL with HTTPS."""
        prompter = HttpPrompter()
        config = {"hostname": "example.com", "kbot_external_root_url": ""}
        result = prompter.prompt_hostname(config, https_port="8443")
        assert result["kbot_external_root_url"] == "https://example.com"

    @patch("builtins.input", return_value="")
    def test_prompt_hostname_external_url_default_http(self, mock_input: Mock) -> None:
        """Test prompt_hostname generates default URL with HTTP."""
        prompter = HttpPrompter()
        config = {"hostname": "example.com", "kbot_external_root_url": ""}
        result = prompter.prompt_hostname(config, https_port=None)
        assert result["kbot_external_root_url"] == "http://example.com"

    @patch("builtins.input", return_value="")
    def test_prompt_hostname_uses_existing_url(self, mock_input: Mock) -> None:
        """Test prompt_hostname uses existing URL from config."""
        prompter = HttpPrompter()
        config = {
            "hostname": "example.com",
            "kbot_external_root_url": "https://existing.example.com",
        }
        result = prompter.prompt_hostname(config)
        assert result["kbot_external_root_url"] == "https://existing.example.com"
