"""Tests for factory module."""

from unittest.mock import MagicMock, patch

import pytest

from kbot_installer.core.auth.pygit_authentication.factory import (
    create_pygit_authentication,
)
from kbot_installer.core.auth.pygit_authentication.pygit_authentication_base import (
    PyGitAuthenticationBase,
)


class TestCreatePygitAuthentication:
    """Test cases for create_pygit_authentication function."""

    @patch("kbot_installer.core.auth.pygit_authentication.factory.factory_method")
    def test_calls_factory_method_with_correct_parameters(
        self, mock_factory_method
    ) -> None:
        """Test that create_pygit_authentication calls factory_method with correct parameters."""
        mock_auth = MagicMock(spec=PyGitAuthenticationBase)
        mock_factory_method.return_value = mock_auth

        result = create_pygit_authentication(
            "test_auth", username="test_user", password="test_pass"
        )

        mock_factory_method.assert_called_once_with(
            "test_auth",
            "kbot_installer.core.auth.pygit_authentication",
            username="test_user",
            password="test_pass",
        )
        assert result == mock_auth

    @patch("kbot_installer.core.auth.pygit_authentication.factory.factory_method")
    def test_returns_factory_method_result(self, mock_factory_method) -> None:
        """Test that create_pygit_authentication returns the result from factory_method."""
        mock_auth = MagicMock(spec=PyGitAuthenticationBase)
        mock_factory_method.return_value = mock_auth

        result = create_pygit_authentication("test_auth")

        assert result == mock_auth

    @patch("kbot_installer.core.auth.pygit_authentication.factory.factory_method")
    def test_passes_kwargs_to_factory_method(self, mock_factory_method) -> None:
        """Test that create_pygit_authentication passes kwargs to factory_method."""
        mock_auth = MagicMock(spec=PyGitAuthenticationBase)
        mock_factory_method.return_value = mock_auth

        kwargs = {
            "username": "test_user",
            "password": "test_pass",
            "private_key_path": "/path/to/key",
        }

        create_pygit_authentication("test_auth", **kwargs)

        mock_factory_method.assert_called_once_with(
            "test_auth", "kbot_installer.core.auth.pygit_authentication", **kwargs
        )

    @patch("kbot_installer.core.auth.pygit_authentication.factory.factory_method")
    def test_handles_factory_method_exceptions(self, mock_factory_method) -> None:
        """Test that create_pygit_authentication handles exceptions from factory_method."""
        mock_factory_method.side_effect = ImportError("Module not found")

        with pytest.raises(ImportError):
            create_pygit_authentication("nonexistent_auth")

    @patch("kbot_installer.core.auth.pygit_authentication.factory.factory_method")
    def test_handles_attribute_error_from_factory_method(
        self, mock_factory_method
    ) -> None:
        """Test that create_pygit_authentication handles AttributeError from factory_method."""
        mock_factory_method.side_effect = AttributeError("Class not found")

        with pytest.raises(AttributeError):
            create_pygit_authentication("invalid_auth")

    @patch("kbot_installer.core.auth.pygit_authentication.factory.factory_method")
    def test_handles_type_error_from_factory_method(self, mock_factory_method) -> None:
        """Test that create_pygit_authentication handles TypeError from factory_method."""
        mock_factory_method.side_effect = TypeError("Invalid arguments")

        with pytest.raises(TypeError):
            create_pygit_authentication("test_auth", invalid_arg="value")

    def test_docstring_contains_examples(self) -> None:
        """Test that the function docstring contains usage examples."""
        docstring = create_pygit_authentication.__doc__
        assert "Example:" in docstring
        assert "create_pygit_authentication" in docstring
        assert "key_pair" in docstring
        assert "user_pass" in docstring
