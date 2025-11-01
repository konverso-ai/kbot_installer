"""Tests for RedisPrompter class."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from kbot_installer.core.interactivity.redis_prompter import RedisPrompter


class TestRedisPrompterPromptRedisParameters:
    """Test cases for RedisPrompter.prompt_redis_parameters."""

    def test_prompt_redis_parameters_basic_installation(self) -> None:
        """Test prompt_redis_parameters with basic installation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            prompter = RedisPrompter()
            config = {"redis_internal": True}
            result = prompter.prompt_redis_parameters(
                config, basic_installation=True, cachedir=temp_dir
            )
            assert result["redis_internal"] is True
            assert "redis_cache_dir" in result

    @patch("builtins.input", return_value="n")
    @patch("builtins.print")
    def test_prompt_redis_parameters_external(
        self, mock_print: Mock, mock_input: Mock
    ) -> None:
        """Test prompt_redis_parameters with external Redis."""
        prompter = RedisPrompter()
        config = {"redis_internal": True}
        result = prompter.prompt_redis_parameters(config, basic_installation=False)
        assert result["redis_internal"] is False

    @patch("builtins.input", return_value="y")
    def test_prompt_redis_parameters_internal(self, mock_input: Mock) -> None:
        """Test prompt_redis_parameters with internal Redis."""
        with tempfile.TemporaryDirectory() as temp_dir:
            prompter = RedisPrompter()
            config = {"redis_internal": False}
            result = prompter.prompt_redis_parameters(
                config, basic_installation=False, cachedir=temp_dir
            )
            assert result["redis_internal"] is True
            assert "redis_cache_dir" in result

    @patch("builtins.input", side_effect=["n", "redis.example.com", "0", "n", "n"])
    @patch("builtins.print")
    def test_prompt_redis_parameters_external_hostname(
        self, mock_print: Mock, mock_input: Mock
    ) -> None:
        """Test prompt_redis_parameters prompts for external hostname."""
        prompter = RedisPrompter()
        config = {"redis_internal": True}
        result = prompter.prompt_redis_parameters(config, basic_installation=False)
        assert result["redis_host"] == "redis.example.com"
        assert result["redis_db_number"] == "0"

    @patch("builtins.input", side_effect=["n", "redis.example.com", "0", "y", "n"])
    @patch("sys.stdin.isatty", return_value=True)
    @patch("getpass.getpass", return_value="redis_password")
    @patch("builtins.print")
    def test_prompt_redis_parameters_external_with_password(
        self, mock_print: Mock, mock_getpass: Mock, mock_isatty: Mock, mock_input: Mock
    ) -> None:
        """Test prompt_redis_parameters prompts for password when secured."""
        prompter = RedisPrompter()
        config = {"redis_internal": True}
        result = prompter.prompt_redis_parameters(config, basic_installation=False)
        assert result["redis_pwd"] == "redis_password"

    @patch(
        "builtins.input", side_effect=["n", "redis.example.com", "0", "n", "y", "6379", "n", "", "", ""]
    )
    @patch("builtins.print")
    def test_prompt_redis_parameters_external_with_tls(
        self, mock_print: Mock, mock_input: Mock
    ) -> None:
        """Test prompt_redis_parameters prompts for TLS port."""
        prompter = RedisPrompter()

        # Mock _port_in_use to return False
        with patch.object(prompter, "_port_in_use", return_value=False):
            config = {"redis_internal": True}
            result = prompter.prompt_redis_parameters(config, basic_installation=False)
            assert result["redis_tls_port"] == "6379"
            assert result["redis_port"] == "0"

    @patch(
        "builtins.input",
        side_effect=["n", "redis.example.com", "0", "n", "y", "6379", "y"],
    )
    @patch("builtins.print")
    def test_prompt_redis_parameters_generate_ssl(
        self, mock_print: Mock, mock_input: Mock
    ) -> None:
        """Test prompt_redis_parameters generates SSL files flag."""
        prompter = RedisPrompter()

        with patch.object(prompter, "_port_in_use", return_value=False):
            config = {"redis_internal": True}
            result = prompter.prompt_redis_parameters(config, basic_installation=False)
            assert result.get("generate_ssl") is True

    @patch(
        "builtins.input",
        side_effect=[
            "n",
            "redis.example.com",
            "0",
            "n",
            "y",
            "6379",
            "n",
            "/path/to/cert",
            "/path/to/key",
            "/path/to/ca",
        ],
    )
    @patch("builtins.print")
    def test_prompt_redis_parameters_external_tls_certificates(
        self, mock_print: Mock, mock_input: Mock
    ) -> None:
        """Test prompt_redis_parameters prompts for TLS certificates."""
        prompter = RedisPrompter()

        with patch.object(prompter, "_port_in_use", return_value=False):
            config = {"redis_internal": True}
            result = prompter.prompt_redis_parameters(config, basic_installation=False)
            assert result["redis_tls_cert_file"] == "/path/to/cert"
            assert result["redis_tls_key_file"] == "/path/to/key"
            assert result["redis_tls_ca_cert_file"] == "/path/to/ca"


class TestRedisPrompterPromptRedisPassword:
    """Test cases for RedisPrompter.prompt_redis_password."""

    @patch("sys.stdin.isatty", return_value=True)
    @patch("getpass.getpass", return_value="redis_password")
    def test_prompt_redis_password(self, mock_getpass: Mock, mock_isatty: Mock) -> None:
        """Test prompt_redis_password."""
        prompter = RedisPrompter()
        result = prompter.prompt_redis_password()
        assert result == "redis_password"


class TestRedisPrompterPortInUse:
    """Test cases for RedisPrompter._port_in_use."""

    @patch("socket.socket")
    def test_port_in_use_true(self, mock_socket: Mock) -> None:
        """Test _port_in_use returns True when port is in use."""
        mock_sock = Mock()
        mock_sock.connect_ex.return_value = 0
        mock_socket.return_value = mock_sock

        prompter = RedisPrompter()
        result = prompter._port_in_use("6379")
        assert result is True
        mock_sock.close.assert_called_once()

    @patch("socket.socket")
    def test_port_in_use_false(self, mock_socket: Mock) -> None:
        """Test _port_in_use returns False when port is not in use."""
        mock_sock = Mock()
        mock_sock.connect_ex.return_value = 1
        mock_socket.return_value = mock_sock

        prompter = RedisPrompter()
        result = prompter._port_in_use("6379")
        assert result is False
        mock_sock.close.assert_called_once()
