"""Tests for SelectorProvider detailed error reporting."""

from unittest.mock import MagicMock

import pytest

from git.provider.base import ProviderBase
from git.provider.errors import ProviderError
from git.provider.selector_provider import SelectorProvider


class TestSelectorProviderErrorDetails:
    """Test cases for detailed error reporting in SelectorProvider."""

    def test_clone_all_providers_fail_detailed_error(self) -> None:
        """Test that all provider failures are reported in detail."""
        mock_storage = MagicMock(spec=ProviderBase)
        mock_storage.clone_and_checkout.side_effect = ProviderError(
            "Version 'release-2021.03-dev' not found for repository 'test-repo'. "
            "Available versions: dev, master, release-2025.03"
        )
        mock_storage.get_name.return_value = "storage"

        mock_github = MagicMock(spec=ProviderBase)
        mock_github.clone_and_checkout.side_effect = ProviderError("Repository 'test-repo' not found")
        mock_github.get_name.return_value = "github"

        mock_bitbucket = MagicMock(spec=ProviderBase)
        mock_bitbucket.clone_and_checkout.side_effect = ProviderError("Authentication failed")
        mock_bitbucket.get_name.return_value = "bitbucket"

        provider = SelectorProvider([mock_storage, mock_github, mock_bitbucket])

        with pytest.raises(ProviderError) as exc_info:
            provider.clone_and_checkout("test-repo", "/tmp/test", branch="release-2021.03-dev")

        error_msg = str(exc_info.value)

        assert "All providers failed to clone repository 'test-repo'" in error_msg
        assert "Version 'release-2021.03-dev' not found" in error_msg
        assert "Repository 'test-repo' not found" in error_msg
        assert "Authentication failed" in error_msg

    def test_clone_unexpected_exception_detailed_error(self) -> None:
        """Test that a non-ProviderError failure is reported with its type and message."""
        mock_provider = MagicMock(spec=ProviderBase)
        mock_provider.clone_and_checkout.side_effect = RuntimeError("connection reset")
        provider = SelectorProvider([mock_provider])

        with pytest.raises(ProviderError) as exc_info:
            provider.clone_and_checkout("test-repo", "/tmp/test")

        error_msg = str(exc_info.value)
        assert "All providers failed to clone repository 'test-repo'" in error_msg
        assert "Unexpected error: RuntimeError: connection reset" in error_msg

    def test_clone_success_returns_early(self) -> None:
        """Test that successful clone returns early without error details."""
        mock_storage = MagicMock(spec=ProviderBase)
        mock_storage.get_name.return_value = "storage"
        mock_github = MagicMock(spec=ProviderBase)
        provider = SelectorProvider([mock_storage, mock_github])

        provider.clone_and_checkout("test-repo", "/tmp/test", branch="release-2021.03-dev")

        mock_storage.clone_and_checkout.assert_called_once()
        mock_github.clone_and_checkout.assert_not_called()
        assert provider.name == "storage"
