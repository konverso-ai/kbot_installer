"""Tests for key_pair_pygit_authentication module."""

from unittest.mock import patch

import pygit2

from kbot_installer.core.auth.pygit_authentication.key_pair_pygit_authentication import (
    KeyPairPygitAuthentication,
)
from kbot_installer.core.auth.pygit_authentication.remote_callback_mixin import (
    RemoteCallbackMixin,
)


class TestKeyPairPygitAuthentication:
    """Test cases for KeyPairPygitAuthentication class."""

    def test_inherits_from_remote_callback_mixin(self) -> None:
        """Test that KeyPairPygitAuthentication inherits from RemoteCallbackMixin."""
        assert issubclass(KeyPairPygitAuthentication, RemoteCallbackMixin)

    def test_initialization(self) -> None:
        """Test proper initialization of KeyPairPygitAuthentication."""
        auth = KeyPairPygitAuthentication(
            username="test_user",
            private_key_path="/path/to/private",
            public_key_path="/path/to/public",
            passphrase="test_passphrase",
        )

        assert auth.username == "test_user"
        assert auth.private_key_path == "/path/to/private"
        assert auth.public_key_path == "/path/to/public"
        assert auth.passphrase == "test_passphrase"

    def test_initialization_with_default_passphrase(self) -> None:
        """Test initialization with default empty passphrase."""
        auth = KeyPairPygitAuthentication(
            username="test_user",
            private_key_path="/path/to/private",
            public_key_path="/path/to/public",
        )

        assert auth.passphrase == ""

    def test_get_credentials_returns_keypair(self) -> None:
        """Test that _get_credentials returns a pygit2.Keypair object."""
        auth = KeyPairPygitAuthentication(
            username="test_user",
            private_key_path="/path/to/private",
            public_key_path="/path/to/public",
            passphrase="test_passphrase",
        )

        credentials = auth._get_credentials()
        assert isinstance(credentials, pygit2.Keypair)

    def test_get_credentials_with_correct_parameters(self) -> None:
        """Test that _get_credentials creates Keypair with correct parameters."""
        auth = KeyPairPygitAuthentication(
            username="test_user",
            private_key_path="/path/to/private",
            public_key_path="/path/to/public",
            passphrase="test_passphrase",
        )

        with patch("pygit2.Keypair") as mock_keypair:
            auth._get_credentials()
            mock_keypair.assert_called_once_with(
                "test_user", "/path/to/public", "/path/to/private", "test_passphrase"
            )

    def test_get_connector_inherited_from_mixin(self) -> None:
        """Test that get_connector is inherited from RemoteCallbackMixin."""
        auth = KeyPairPygitAuthentication(
            username="test_user",
            private_key_path="/path/to/private",
            public_key_path="/path/to/public",
        )

        # Should not raise AttributeError
        assert hasattr(auth, "get_connector")
        assert callable(auth.get_connector)
