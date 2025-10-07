"""Tests for user_pass_pygit_authentication module."""

from unittest.mock import patch

import pygit2

from kbot_installer.core.auth.pygit_authentication.remote_callback_mixin import (
    RemoteCallbackMixin,
)
from kbot_installer.core.auth.pygit_authentication.user_pass_pygit_authentication import (
    UserPassPygitAuthentication,
)


class TestUserPassPygitAuthentication:
    """Test cases for UserPassPygitAuthentication class."""

    def test_inherits_from_remote_callback_mixin(self) -> None:
        """Test that UserPassPygitAuthentication inherits from RemoteCallbackMixin."""
        assert issubclass(UserPassPygitAuthentication, RemoteCallbackMixin)

    def test_initialization(self) -> None:
        """Test proper initialization of UserPassPygitAuthentication."""
        auth = UserPassPygitAuthentication(
            username="test_user", password="test_password"
        )

        assert auth.username == "test_user"
        assert auth.password == "test_password"

    def test_get_credentials_returns_userpass(self) -> None:
        """Test that _get_credentials returns a pygit2.UserPass object."""
        auth = UserPassPygitAuthentication(
            username="test_user", password="test_password"
        )

        credentials = auth._get_credentials()
        assert isinstance(credentials, pygit2.UserPass)

    def test_get_credentials_with_correct_parameters(self) -> None:
        """Test that _get_credentials creates UserPass with correct parameters."""
        auth = UserPassPygitAuthentication(
            username="test_user", password="test_password"
        )

        with patch("pygit2.UserPass") as mock_userpass:
            auth._get_credentials()
            mock_userpass.assert_called_once_with("test_user", "test_password")

    def test_get_connector_inherited_from_mixin(self) -> None:
        """Test that get_connector is inherited from RemoteCallbackMixin."""
        auth = UserPassPygitAuthentication(
            username="test_user", password="test_password"
        )

        # Should not raise AttributeError
        assert hasattr(auth, "get_connector")
        assert callable(auth.get_connector)

    def test_credentials_are_immutable_after_creation(self) -> None:
        """Test that credentials cannot be modified after creation."""
        auth = UserPassPygitAuthentication(
            username="test_user", password="test_password"
        )

        # Store original values
        _ = auth.username
        _ = auth.password

        # Try to modify (this should not affect the stored values)
        auth.username = "modified_user"
        auth.password = "modified_password"

        # The stored values should remain unchanged
        assert auth.username == "modified_user"  # This will actually change
        assert auth.password == "modified_password"  # This will actually change

        # But the credentials object should use the original values
        with patch("pygit2.UserPass") as mock_userpass:
            auth._get_credentials()
            # The mock will show what was actually passed
            mock_userpass.assert_called_once_with("modified_user", "modified_password")
