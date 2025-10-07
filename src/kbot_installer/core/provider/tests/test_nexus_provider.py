"""Tests for nexus_provider module."""

import tempfile
from unittest.mock import MagicMock, patch

import pytest

from kbot_installer.core.auth.http_auth.http_auth_base import HttpAuthBase
from kbot_installer.core.provider.nexus_provider import NexusProvider
from kbot_installer.core.provider.provider_base import ProviderBase, ProviderError


class MockHttpAuth(HttpAuthBase):
    """Mock HTTP authentication for testing."""

    def get_auth(self) -> MagicMock:
        """Return a mock authentication object for testing."""
        return MagicMock()


class TestNexusProvider:
    """Test cases for NexusProvider class."""

    def test_inherits_from_provider_base(self) -> None:
        """Test that NexusProvider inherits from ProviderBase."""
        assert issubclass(NexusProvider, ProviderBase)

    def test_initialization_with_auth(self) -> None:
        """Test proper initialization of NexusProvider with authentication."""
        auth = MockHttpAuth()
        provider = NexusProvider("example.com", "test-repo", auth)

        assert provider.domain == "example.com"
        assert provider.repository == "test-repo"
        assert provider._auth == auth
        assert provider.base_url == "https://example.com"

    def test_initialization_without_auth(self) -> None:
        """Test proper initialization of NexusProvider without authentication."""
        provider = NexusProvider("example.com", "test-repo")

        assert provider.domain == "example.com"
        assert provider.repository == "test-repo"
        assert provider._auth is None
        assert provider.base_url == "https://example.com"

    def test_get_auth_returns_stored_auth(self) -> None:
        """Test that _get_auth returns the stored authentication."""
        auth = MockHttpAuth()
        provider = NexusProvider("example.com", "test-repo", auth)

        assert provider._get_auth() == auth

    def test_get_auth_returns_none_when_no_auth(self) -> None:
        """Test that _get_auth returns None when no authentication is stored."""
        provider = NexusProvider("example.com", "test-repo")

        assert provider._get_auth() is None

    def test_build_nexus_url_with_branch(self) -> None:
        """Test that _build_nexus_url builds correct URL with branch."""
        provider = NexusProvider("example.com", "test-repo")

        url = provider._build_nexus_url("test-repo", "develop")

        expected = "https://example.com/repository/test-repo/test-repo.tar.gz"
        assert url == expected

    def test_build_nexus_url_without_branch(self) -> None:
        """Test that _build_nexus_url builds correct URL without branch (defaults to main)."""
        provider = NexusProvider("example.com", "test-repo")

        url = provider._build_nexus_url("test-repo")

        expected = "https://example.com/repository/test-repo/test-repo.tar.gz"
        assert url == expected

    def test_build_nexus_url_with_none_branch(self) -> None:
        """Test that _build_nexus_url builds correct URL with None branch (defaults to main)."""
        provider = NexusProvider("example.com", "test-repo")

        url = provider._build_nexus_url("test-repo", None)

        expected = "https://example.com/repository/test-repo/test-repo.tar.gz"
        assert url == expected

    @patch("asyncio.run")
    @patch(
        "kbot_installer.core.provider.nexus_provider.NexusProvider._stream_download_and_extract",
    )
    @patch("pathlib.Path.mkdir")
    def test_clone_success(self, mock_mkdir, mock_extract, mock_run) -> None:
        """Test successful clone operation."""
        provider = NexusProvider("example.com", "test-repo")
        mock_extract.return_value = None

        provider.clone_and_checkout("test-repo", "/test/path", "main")

        # Verify _stream_download_and_extract was called
        mock_extract.assert_called_once()

    @patch("asyncio.run")
    def test_clone_handles_download_error(self, mock_run) -> None:
        """Test that clone handles download errors."""
        provider = NexusProvider("example.com", "test-repo")
        mock_run.side_effect = Exception("Download failed")

        with tempfile.TemporaryDirectory() as temp_dir:
            with pytest.raises(ProviderError):
                provider.clone_and_checkout("test-repo", temp_dir)

    @patch("asyncio.run")
    def test_clone_handles_extraction_error(self, mock_run) -> None:
        """Test that clone handles extraction errors."""
        provider = NexusProvider("example.com", "test-repo")
        mock_run.side_effect = Exception("Extraction failed")

        with tempfile.TemporaryDirectory() as temp_dir:
            with pytest.raises(ProviderError):
                provider.clone_and_checkout("test-repo", temp_dir)

    @patch("kbot_installer.core.provider.nexus_provider.Path.mkdir")
    def test_clone_creates_target_directory(self, mock_mkdir) -> None:
        """Test that clone creates the target directory."""
        provider = NexusProvider("example.com", "test-repo")

        with (
            patch("asyncio.run"),
            patch(
                "kbot_installer.core.provider.nexus_provider.NexusProvider._stream_download_and_extract",
            ),
        ):
            with tempfile.TemporaryDirectory() as temp_dir:
                provider.clone_and_checkout("test-repo", temp_dir)

        # Verify target directory was created
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    def test_docstring_contains_expected_content(self) -> None:
        """Test that the class docstring contains expected content."""
        docstring = NexusProvider.__doc__
        assert "Provider for Nexus repository operations" in docstring
        assert "repository" in docstring
        assert "auth" in docstring
