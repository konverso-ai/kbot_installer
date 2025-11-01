"""Tests for AdminPrompter class."""

from unittest.mock import Mock, patch

from kbot_installer.core.interactivity.admin_prompter import AdminPrompter


class TestAdminPrompter:
    """Test cases for AdminPrompter."""

    @patch("sys.stdin.isatty", return_value=True)
    @patch("getpass.getpass", side_effect=["admin123", "admin123"])
    def test_prompt_admin_password_with_confirmation(
        self, mock_getpass: Mock, mock_isatty: Mock
    ) -> None:
        """Test prompt_admin_password with confirmation."""
        prompter = AdminPrompter()
        result = prompter.prompt_admin_password()
        assert result == "admin123"
        assert mock_getpass.call_count == 2

    @patch("sys.stdin.isatty", return_value=True)
    @patch("getpass.getpass", side_effect=["admin123", "admin123"])
    def test_prompt_admin_password_with_validator_pass(
        self, mock_getpass: Mock, mock_isatty: Mock
    ) -> None:
        """Test prompt_admin_password with validator that passes."""
        prompter = AdminPrompter()

        def validator(pwd: str) -> bool:
            return len(pwd) >= 8

        result = prompter.prompt_admin_password(password_validator=validator)
        assert result == "admin123"

    @patch("sys.stdin.isatty", return_value=True)
    @patch("getpass.getpass", side_effect=["weak", "admin123", "admin123"])
    @patch("builtins.print")
    def test_prompt_admin_password_with_validator_fail_then_pass(
        self, mock_print: Mock, mock_getpass: Mock, mock_isatty: Mock
    ) -> None:
        """Test prompt_admin_password with validator that fails then passes."""
        prompter = AdminPrompter()

        def validator(pwd: str) -> bool:
            return len(pwd) >= 8

        result = prompter.prompt_admin_password(password_validator=validator)
        assert result == "admin123"

    def test_prompt_admin_password_with_default(self) -> None:
        """Test prompt_admin_password with default password."""
        prompter = AdminPrompter()
        result = prompter.prompt_admin_password(default_password="default123")
        assert result == "default123"

    def test_prompt_admin_password_with_encrypt_fn(self) -> None:
        """Test prompt_admin_password with encryption function."""
        prompter = AdminPrompter()

        def encrypt_fn(password: str) -> str:
            return f"encrypted_{password}"

        result = prompter.prompt_admin_password(
            default_password="admin123", encrypt_fn=encrypt_fn
        )
        assert result == "encrypted_admin123"

    @patch("sys.stdin.isatty", return_value=True)
    @patch("getpass.getpass", side_effect=["admin123", "admin123"])
    def test_prompt_admin_password_with_encrypt_fn_no_default(
        self, mock_getpass: Mock, mock_isatty: Mock
    ) -> None:
        """Test prompt_admin_password with encryption function and no default."""
        prompter = AdminPrompter()

        def encrypt_fn(password: str) -> str:
            return f"encrypted_{password}"

        result = prompter.prompt_admin_password(encrypt_fn=encrypt_fn)
        assert result == "encrypted_admin123"

    @patch("sys.stdin.isatty", return_value=True)
    @patch("getpass.getpass", side_effect=["admin123", "admin123"])
    def test_prompt_admin_password_with_validator_and_encrypt_fn(
        self, mock_getpass: Mock, mock_isatty: Mock
    ) -> None:
        """Test prompt_admin_password with both validator and encrypt_fn."""
        prompter = AdminPrompter()

        def validator(pwd: str) -> bool:
            return len(pwd) >= 8

        def encrypt_fn(password: str) -> str:
            return f"encrypted_{password}"

        result = prompter.prompt_admin_password(
            password_validator=validator, encrypt_fn=encrypt_fn
        )
        assert result == "encrypted_admin123"


