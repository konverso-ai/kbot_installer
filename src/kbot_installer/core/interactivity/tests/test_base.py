"""Tests for InteractivePrompter base class."""

from unittest.mock import Mock, patch

from kbot_installer.core.interactivity.base import InteractivePrompter


class TestInteractivePrompterInitialization:
    """Test cases for InteractivePrompter initialization."""

    def test_init_defaults(self) -> None:
        """Test initialization with default values."""
        prompter = InteractivePrompter()
        assert prompter.use_defaults is False
        assert prompter.silent is False

    def test_init_use_defaults(self) -> None:
        """Test initialization with use_defaults=True."""
        prompter = InteractivePrompter(use_defaults=True)
        assert prompter.use_defaults is True
        assert prompter.silent is False

    def test_init_silent(self) -> None:
        """Test initialization with silent=True."""
        prompter = InteractivePrompter(silent=True)
        assert prompter.use_defaults is False
        assert prompter.silent is True

    def test_init_both(self) -> None:
        """Test initialization with both use_defaults and silent."""
        prompter = InteractivePrompter(use_defaults=True, silent=True)
        assert prompter.use_defaults is True
        assert prompter.silent is True


class TestInteractivePrompterAskYN:
    """Test cases for ask_yn method."""

    @patch("builtins.input", return_value="y")
    def test_ask_yn_yes(self, mock_input: Mock) -> None:
        """Test ask_yn with 'y' input."""
        prompter = InteractivePrompter()
        result = prompter.ask_yn("Do you want to continue?")
        assert result is True
        mock_input.assert_called_once()

    @patch("builtins.input", return_value="yes")
    def test_ask_yn_yes_full(self, mock_input: Mock) -> None:
        """Test ask_yn with 'yes' input."""
        prompter = InteractivePrompter()
        result = prompter.ask_yn("Do you want to continue?")
        assert result is True

    @patch("builtins.input", return_value="n")
    def test_ask_yn_no(self, mock_input: Mock) -> None:
        """Test ask_yn with 'n' input."""
        prompter = InteractivePrompter()
        result = prompter.ask_yn("Do you want to continue?")
        assert result is False

    @patch("builtins.input", return_value="no")
    def test_ask_yn_no_full(self, mock_input: Mock) -> None:
        """Test ask_yn with 'no' input."""
        prompter = InteractivePrompter()
        result = prompter.ask_yn("Do you want to continue?")
        assert result is False

    @patch("builtins.input", return_value="")
    @patch("builtins.print")
    def test_ask_yn_default_empty(self, mock_print: Mock, mock_input: Mock) -> None:
        """Test ask_yn with empty input uses default."""
        prompter = InteractivePrompter()
        result = prompter.ask_yn("Continue?", default="y")
        assert result is True

    @patch("builtins.input", return_value="")
    @patch("builtins.print")
    def test_ask_yn_default_n(self, mock_print: Mock, mock_input: Mock) -> None:
        """Test ask_yn with empty input and default 'n'."""
        prompter = InteractivePrompter()
        result = prompter.ask_yn("Continue?", default="n")
        assert result is False

    @patch("builtins.input", side_effect=["maybe", "y"])
    @patch("builtins.print")
    def test_ask_yn_invalid_then_valid(
        self, mock_print: Mock, mock_input: Mock
    ) -> None:
        """Test ask_yn with invalid input then valid."""
        prompter = InteractivePrompter()
        result = prompter.ask_yn("Continue?")
        assert result is True
        assert mock_input.call_count == 2
        mock_print.assert_called_once_with('Answer either "y" or "n".')

    def test_ask_yn_use_defaults(self) -> None:
        """Test ask_yn with use_defaults=True."""
        prompter = InteractivePrompter(use_defaults=True)
        result = prompter.ask_yn("Continue?")
        assert result is True


class TestInteractivePrompterAskPort:
    """Test cases for ask_port method."""

    @patch("builtins.input", return_value="8080")
    def test_ask_port_valid(self, mock_input: Mock) -> None:
        """Test ask_port with valid port number."""
        prompter = InteractivePrompter()
        result = prompter.ask_port("Enter port:", "8080", "http")
        assert result == "8080"

    @patch("builtins.input", return_value="")
    def test_ask_port_default(self, mock_input: Mock) -> None:
        """Test ask_port with empty input uses default."""
        prompter = InteractivePrompter()
        result = prompter.ask_port("Enter port:", "8080", "http")
        assert result == "8080"

    @patch("builtins.input", side_effect=["500", "8080"])
    @patch("builtins.print")
    def test_ask_port_too_low(self, mock_print: Mock, mock_input: Mock) -> None:
        """Test ask_port with port below 1024."""
        prompter = InteractivePrompter()
        result = prompter.ask_port("Enter port:", "8080", "http")
        assert result == "8080"
        assert mock_input.call_count == 2

    @patch("builtins.input", side_effect=["70000", "8080"])
    @patch("builtins.print")
    def test_ask_port_too_high(self, mock_print: Mock, mock_input: Mock) -> None:
        """Test ask_port with port above 65535."""
        prompter = InteractivePrompter()
        result = prompter.ask_port("Enter port:", "8080", "http")
        assert result == "8080"
        assert mock_input.call_count == 2

    @patch("builtins.input", side_effect=["abc", "8080"])
    @patch("builtins.print")
    def test_ask_port_non_numeric(self, mock_print: Mock, mock_input: Mock) -> None:
        """Test ask_port with non-numeric input."""
        prompter = InteractivePrompter()
        result = prompter.ask_port("Enter port:", "8080", "http")
        assert result == "8080"
        assert mock_input.call_count == 2

    @patch("builtins.input", side_effect=["8080", "8443"])
    @patch("builtins.print")
    def test_ask_port_http_https_conflict(
        self, mock_print: Mock, mock_input: Mock
    ) -> None:
        """Test ask_port with HTTP port conflicting with HTTPS."""
        prompter = InteractivePrompter()
        result = prompter.ask_port(
            "Enter HTTP port:", "8080", "http", https_port="8080"
        )
        assert result == "8443"
        assert mock_input.call_count == 2

    @patch("builtins.input", side_effect=["8443", "8080"])
    @patch("builtins.print")
    def test_ask_port_https_http_conflict(
        self, mock_print: Mock, mock_input: Mock
    ) -> None:
        """Test ask_port with HTTPS port conflicting with HTTP."""
        prompter = InteractivePrompter()
        result = prompter.ask_port(
            "Enter HTTPS port:", "8443", "https", http_port="8443"
        )
        assert result == "8080"
        assert mock_input.call_count == 2

    @patch("builtins.input", return_value="8080")
    def test_ask_port_no_limit(self, mock_input: Mock) -> None:
        """Test ask_port with limit=False allows any port."""
        prompter = InteractivePrompter()
        result = prompter.ask_port("Enter port:", "500", "http", limit=False)
        assert result == "8080"


class TestInteractivePrompterAskInput:
    """Test cases for ask_input method."""

    @patch("builtins.input", return_value="test_value")
    def test_ask_input_valid(self, mock_input: Mock) -> None:
        """Test ask_input with valid input."""
        prompter = InteractivePrompter()
        result = prompter.ask_input("Enter value:")
        assert result == "test_value"

    @patch("builtins.input", return_value="")
    def test_ask_input_empty_with_default(self, mock_input: Mock) -> None:
        """Test ask_input with empty input and default."""
        prompter = InteractivePrompter()
        result = prompter.ask_input("Enter value:", default="default_value")
        assert result == "default_value"

    @patch("builtins.input", return_value="")
    def test_ask_input_empty_no_default(self, mock_input: Mock) -> None:
        """Test ask_input with empty input and no default."""
        prompter = InteractivePrompter()
        result = prompter.ask_input("Enter value:")
        assert result == ""

    @patch("builtins.input", return_value="  test  ")
    def test_ask_input_strips_whitespace(self, mock_input: Mock) -> None:
        """Test ask_input strips whitespace."""
        prompter = InteractivePrompter()
        result = prompter.ask_input("Enter value:")
        assert result == "test"

    def test_ask_input_use_defaults(self) -> None:
        """Test ask_input with use_defaults=True."""
        prompter = InteractivePrompter(use_defaults=True)
        result = prompter.ask_input("Enter value:", default="default_value")
        assert result == "default_value"


class TestInteractivePrompterAskPassword:
    """Test cases for ask_password method."""

    @patch("sys.stdin.isatty", return_value=True)
    @patch("getpass.getpass", side_effect=["password123", "password123"])
    def test_ask_password_with_confirmation(
        self, mock_getpass: Mock, mock_isatty: Mock
    ) -> None:
        """Test ask_password with confirmation."""
        prompter = InteractivePrompter()
        result = prompter.ask_password("Enter password:", confirm=True)
        assert result == "password123"
        assert mock_getpass.call_count == 2

    @patch("sys.stdin.isatty", return_value=True)
    @patch("getpass.getpass", return_value="password123")
    def test_ask_password_no_confirmation(
        self, mock_getpass: Mock, mock_isatty: Mock
    ) -> None:
        """Test ask_password without confirmation."""
        prompter = InteractivePrompter()
        result = prompter.ask_password("Enter password:", confirm=False)
        assert result == "password123"
        mock_getpass.assert_called_once()

    @patch("sys.stdin.isatty", return_value=True)
    @patch(
        "getpass.getpass",
        side_effect=["password123", "password456", "password789", "password789"],
    )
    @patch("builtins.print")
    def test_ask_password_mismatch_then_match(
        self, mock_print: Mock, mock_getpass: Mock, mock_isatty: Mock
    ) -> None:
        """Test ask_password with mismatched passwords then match."""
        prompter = InteractivePrompter()
        result = prompter.ask_password("Enter password:", confirm=True)
        assert result == "password789"
        assert mock_getpass.call_count == 4

    @patch("sys.stdin.isatty", return_value=True)
    @patch("getpass.getpass", side_effect=["", "password123", "password123"])
    @patch("builtins.print")
    def test_ask_password_empty_then_valid(
        self, mock_print: Mock, mock_getpass: Mock, mock_isatty: Mock
    ) -> None:
        """Test ask_password with empty password then valid."""
        prompter = InteractivePrompter()
        result = prompter.ask_password("Enter password:", confirm=True)
        assert result == "password123"
        assert mock_getpass.call_count == 3

    def test_ask_password_with_default(self) -> None:
        """Test ask_password with default value."""
        prompter = InteractivePrompter()
        result = prompter.ask_password("Enter password:", default="default_pass")
        assert result == "default_pass"

    @patch("sys.stdin.isatty", return_value=False)
    @patch("builtins.print")
    @patch("sys.stdin.readline", return_value="password123\n")
    def test_ask_password_non_tty(
        self, mock_readline: Mock, mock_print: Mock, mock_isatty: Mock
    ) -> None:
        """Test ask_password when stdin is not a TTY."""
        prompter = InteractivePrompter()
        result = prompter.ask_password("Enter password:", confirm=False)
        assert result == "password123"

    @patch("sys.stdin.isatty", return_value=True)
    @patch("getpass.getpass", return_value="weak")
    @patch("builtins.print")
    def test_ask_password_with_validator_pass(
        self, mock_print: Mock, mock_getpass: Mock, mock_isatty: Mock
    ) -> None:
        """Test ask_password with validator that passes."""
        prompter = InteractivePrompter()

        def validator(pwd: str) -> bool:
            return len(pwd) >= 4

        result = prompter.ask_password(
            "Enter password:", validator=validator, confirm=False
        )
        assert result == "weak"

    @patch("sys.stdin.isatty", return_value=True)
    @patch("getpass.getpass", side_effect=["weak", "strong123"])
    @patch("builtins.print")
    def test_ask_password_with_validator_fail_then_pass(
        self, mock_print: Mock, mock_getpass: Mock, mock_isatty: Mock
    ) -> None:
        """Test ask_password with validator that fails then passes."""
        prompter = InteractivePrompter()

        def validator(pwd: str) -> bool:
            return len(pwd) >= 8

        result = prompter.ask_password(
            "Enter password:", validator=validator, confirm=False
        )
        assert result == "strong123"
        assert mock_print.call_count == 1
