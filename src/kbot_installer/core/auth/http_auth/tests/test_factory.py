"""Tests for factory module."""

from unittest.mock import MagicMock, patch

import pytest

from kbot_installer.core.auth.http_auth.factory import create_http_auth
from kbot_installer.core.auth.http_auth.http_auth_base import HttpAuthBase


class TestCreateHttpAuth:
    """Test cases for create_http_auth function."""

    @patch("kbot_installer.core.auth.http_auth.factory.factory_method")
    def test_calls_factory_method_with_correct_parameters(
        self, mock_factory_method
    ) -> None:
        """Test that create_http_auth calls factory_method with correct parameters."""
        mock_auth = MagicMock(spec=HttpAuthBase)
        mock_factory_method.return_value = mock_auth

        result = create_http_auth(
            "test_auth", username="test_user", password="test_pass"
        )

        mock_factory_method.assert_called_once_with(
            "test_auth",
            "kbot_installer.core.auth.http_auth",
            username="test_user",
            password="test_pass",
        )
        assert result == mock_auth

    @patch("kbot_installer.core.auth.http_auth.factory.factory_method")
    def test_returns_factory_method_result(self, mock_factory_method) -> None:
        """Test that create_http_auth returns the result from factory_method."""
        mock_auth = MagicMock(spec=HttpAuthBase)
        mock_factory_method.return_value = mock_auth

        result = create_http_auth("test_auth")

        assert result == mock_auth

    @patch("kbot_installer.core.auth.http_auth.factory.factory_method")
    def test_passes_kwargs_to_factory_method(self, mock_factory_method) -> None:
        """Test that create_http_auth passes kwargs to factory_method."""
        mock_auth = MagicMock(spec=HttpAuthBase)
        mock_factory_method.return_value = mock_auth

        kwargs = {
            "username": "test_user",
            "password": "test_pass",
            "token": "test_token",
        }

        create_http_auth("test_auth", **kwargs)

        mock_factory_method.assert_called_once_with(
            "test_auth", "kbot_installer.core.auth.http_auth", **kwargs
        )

    @patch("kbot_installer.core.auth.http_auth.factory.factory_method")
    def test_handles_factory_method_exceptions(self, mock_factory_method) -> None:
        """Test that create_http_auth handles exceptions from factory_method."""
        mock_factory_method.side_effect = ImportError("Module not found")

        with pytest.raises(ImportError):
            create_http_auth("nonexistent_auth")

    @patch("kbot_installer.core.auth.http_auth.factory.factory_method")
    def test_handles_attribute_error_from_factory_method(
        self, mock_factory_method
    ) -> None:
        """Test that create_http_auth handles AttributeError from factory_method."""
        mock_factory_method.side_effect = AttributeError("Class not found")

        with pytest.raises(AttributeError):
            create_http_auth("invalid_auth")

    @patch("kbot_installer.core.auth.http_auth.factory.factory_method")
    def test_handles_type_error_from_factory_method(self, mock_factory_method) -> None:
        """Test that create_http_auth handles TypeError from factory_method."""
        mock_factory_method.side_effect = TypeError("Invalid arguments")

        with pytest.raises(TypeError):
            create_http_auth("test_auth", invalid_arg="value")

    def test_docstring_contains_examples(self) -> None:
        """Test that the function docstring contains usage examples."""
        docstring = create_http_auth.__doc__
        assert "Example:" in docstring
        assert "create_http_auth" in docstring
        assert "basic" in docstring
        assert "bearer" in docstring
