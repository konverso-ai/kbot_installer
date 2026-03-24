"""Tests for bearer_http_auth module."""

from unittest.mock import MagicMock

import httpx

from kbot_installer.core.auth.http_auth.bearer_http_auth import BearerHttpAuth
from kbot_installer.core.auth.http_auth.http_auth_base import HttpAuthBase


class TestBearerHttpAuth:
    """Test cases for BearerHttpAuth class."""

    def test_inherits_from_http_auth_base_and_httpx_auth(self) -> None:
        """Test that BearerHttpAuth inherits from both HttpAuthBase and httpx.Auth."""
        assert issubclass(BearerHttpAuth, HttpAuthBase)
        assert issubclass(BearerHttpAuth, httpx.Auth)

    def test_initialization(self) -> None:
        """Test proper initialization of BearerHttpAuth."""
        auth = BearerHttpAuth("test_token")

        assert auth.token == "test_token"

    def test_get_auth_returns_self(self) -> None:
        """Test that get_auth returns self."""
        auth = BearerHttpAuth("test_token")

        result = auth.get_auth()
        assert result is auth

    def test_auth_flow_adds_authorization_header(self) -> None:
        """Test that auth_flow adds Authorization header with Bearer token."""
        auth = BearerHttpAuth("test_token")

        # Create a mock request
        mock_request = MagicMock()
        mock_request.headers = {}

        # Call auth_flow
        result = list(auth.auth_flow(mock_request))

        # Should yield one request
        assert len(result) == 1
        assert result[0] is mock_request

        # Check that Authorization header was set
        assert mock_request.headers["Authorization"] == "Bearer test_token"

    def test_auth_flow_preserves_existing_headers(self) -> None:
        """Test that auth_flow preserves existing headers."""
        auth = BearerHttpAuth("test_token")

        # Create a mock request with existing headers
        mock_request = MagicMock()
        mock_request.headers = {"Content-Type": "application/json"}

        # Call auth_flow
        list(auth.auth_flow(mock_request))

        # Check that existing headers are preserved
        assert mock_request.headers["Content-Type"] == "application/json"
        assert mock_request.headers["Authorization"] == "Bearer test_token"

    def test_auth_flow_is_generator(self) -> None:
        """Test that auth_flow is a generator function."""
        auth = BearerHttpAuth("test_token")

        mock_request = MagicMock()
        mock_request.headers = {}

        # Should return an iterator
        result = auth.auth_flow(mock_request)
        assert hasattr(result, "__iter__")
        assert hasattr(result, "__next__")

    def test_multiple_instances_independence(self) -> None:
        """Test that multiple instances are independent."""
        auth1 = BearerHttpAuth("token1")
        auth2 = BearerHttpAuth("token2")

        assert auth1.token != auth2.token

        mock_request1 = MagicMock()
        mock_request1.headers = {}
        mock_request2 = MagicMock()
        mock_request2.headers = {}

        list(auth1.auth_flow(mock_request1))
        list(auth2.auth_flow(mock_request2))

        assert mock_request1.headers["Authorization"] == "Bearer token1"
        assert mock_request2.headers["Authorization"] == "Bearer token2"

    def test_empty_token_handling(self) -> None:
        """Test handling of empty token."""
        auth = BearerHttpAuth("")

        mock_request = MagicMock()
        mock_request.headers = {}

        list(auth.auth_flow(mock_request))

        assert mock_request.headers["Authorization"] == "Bearer "

    def test_special_characters_in_token(self) -> None:
        """Test handling of special characters in token."""
        special_token = "token-with-special.chars+123"
        auth = BearerHttpAuth(special_token)

        mock_request = MagicMock()
        mock_request.headers = {}

        list(auth.auth_flow(mock_request))

        assert mock_request.headers["Authorization"] == f"Bearer {special_token}"
