"""Tests for basic_http_auth module."""

from unittest.mock import patch

import httpx

from kbot_installer.core.auth.http_auth.basic_http_auth import BasicHttpAuth
from kbot_installer.core.auth.http_auth.http_auth_base import HttpAuthBase


class TestBasicHttpAuth:
    """Test cases for BasicHttpAuth class."""

    def test_inherits_from_http_auth_base(self) -> None:
        """Test that BasicHttpAuth inherits from HttpAuthBase."""
        assert issubclass(BasicHttpAuth, HttpAuthBase)

    def test_initialization(self) -> None:
        """Test proper initialization of BasicHttpAuth."""
        auth = BasicHttpAuth(username="test_user", password="test_password")

        assert auth.username == "test_user"
        assert auth.password == "test_password"

    def test_get_auth_returns_basic_auth(self) -> None:
        """Test that get_auth returns a httpx.BasicAuth object."""
        auth = BasicHttpAuth(username="test_user", password="test_password")

        result = auth.get_auth()
        assert isinstance(result, httpx.BasicAuth)

    def test_get_auth_with_correct_parameters(self) -> None:
        """Test that get_auth creates BasicAuth with correct parameters."""
        auth = BasicHttpAuth(username="test_user", password="test_password")

        with patch("httpx.BasicAuth") as mock_basic_auth:
            auth.get_auth()
            mock_basic_auth.assert_called_once_with("test_user", "test_password")

    def test_basic_auth_inherits_from_httpx_auth(self) -> None:
        """Test that the returned BasicAuth inherits from httpx.Auth."""
        auth = BasicHttpAuth(username="test_user", password="test_password")

        result = auth.get_auth()
        assert isinstance(result, httpx.Auth)

    def test_credentials_are_stored_correctly(self) -> None:
        """Test that credentials are stored correctly during initialization."""
        username = "my_username"
        password = "my_password"

        auth = BasicHttpAuth(username, password)

        assert auth.username == username
        assert auth.password == password

    def test_multiple_instances_independence(self) -> None:
        """Test that multiple instances are independent."""
        auth1 = BasicHttpAuth("user1", "pass1")
        auth2 = BasicHttpAuth("user2", "pass2")

        assert auth1.username != auth2.username
        assert auth1.password != auth2.password

        result1 = auth1.get_auth()
        result2 = auth2.get_auth()

        # Results should be different objects
        assert result1 is not result2
