"""Tests for bitbucket_provider module."""

from unittest.mock import MagicMock, patch

import pytest

from kbot_installer.core.auth.pygit_authentication import PyGitAuthenticationBase
from kbot_installer.core.provider.bitbucket_provider import BitbucketProvider
from kbot_installer.core.provider.provider_base import ProviderBase


class TestBitbucketProvider:
    """Test cases for BitbucketProvider class."""

    def test_inherits_from_provider_base(self) -> None:
        """Test that BitbucketProvider inherits from ProviderBase."""
        assert issubclass(BitbucketProvider, ProviderBase)

    def test_initialization_with_auth(self) -> None:
        """Test proper initialization of BitbucketProvider with authentication."""
        mock_auth = MagicMock(spec=PyGitAuthenticationBase)
        provider = BitbucketProvider("test_account", mock_auth)

        assert provider.account_name == "test_account"
        assert provider._auth == mock_auth
        assert (
            provider.base_url
            == "https://{name}.org/{account_name}/{repository_name}.git"
        )

    def test_initialization_without_auth(self) -> None:
        """Test proper initialization of BitbucketProvider without authentication."""
        provider = BitbucketProvider("test_account")

        assert provider.account_name == "test_account"
        assert provider._auth is None
        assert (
            provider.base_url
            == "https://{name}.org/{account_name}/{repository_name}.git"
        )

    def test_get_auth_with_auth(self) -> None:
        """Test that _get_auth returns the authentication object when provided."""
        mock_auth = MagicMock(spec=PyGitAuthenticationBase)
        provider = BitbucketProvider("test_account", mock_auth)

        assert provider._get_auth() == mock_auth

    def test_get_auth_without_auth(self) -> None:
        """Test that _get_auth returns None when no authentication is provided."""
        provider = BitbucketProvider("test_account")

        assert provider._get_auth() is None

    @pytest.mark.asyncio
    @patch(
        "kbot_installer.core.provider.bitbucket_provider.GitMixin.clone_and_checkout"
    )
    async def test_clone_calls_parent_clone(self, mock_clone) -> None:
        """Test that clone calls the parent clone method."""
        provider = BitbucketProvider("test_account")
        await provider.clone_and_checkout("test_repo", "/test/path", "main")

        mock_clone.assert_called_once_with(
            "https://bitbucket.org/test_account/test_repo.git", "/test/path", "main"
        )

    @pytest.mark.asyncio
    @patch(
        "kbot_installer.core.provider.bitbucket_provider.GitMixin.clone_and_checkout"
    )
    async def test_clone_without_branch(self, mock_clone) -> None:
        """Test that clone works without specifying branch."""
        provider = BitbucketProvider("test_account")
        await provider.clone_and_checkout("test_repo", "/test/path")

        mock_clone.assert_called_once_with(
            "https://bitbucket.org/test_account/test_repo.git", "/test/path", None
        )

    @pytest.mark.asyncio
    @patch(
        "kbot_installer.core.provider.bitbucket_provider.GitMixin.clone_and_checkout"
    )
    async def test_clone_with_different_branch(self, mock_clone) -> None:
        """Test that clone works with different branch."""
        provider = BitbucketProvider("test_account")
        await provider.clone_and_checkout("test_repo", "/test/path", "develop")

        mock_clone.assert_called_once_with(
            "https://bitbucket.org/test_account/test_repo.git", "/test/path", "develop"
        )

    @pytest.mark.asyncio
    async def test_check_remote_repository_exists_success(self) -> None:
        """Test check_remote_repository_exists returns True when repository exists."""
        provider = BitbucketProvider("test_account")

        with patch.object(provider, "_get_versioner") as mock_get_versioner:
            mock_versioner = MagicMock()

            # Create an async mock for check_remote_repository_exists
            async def async_check_remote_repository_exists(_url):
                return True

            mock_versioner.check_remote_repository_exists = (
                async_check_remote_repository_exists
            )
            mock_get_versioner.return_value = mock_versioner

            result = await provider.check_remote_repository_exists("test_repo")

            assert result is True
            mock_get_versioner.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_remote_repository_exists_failure(self) -> None:
        """Test check_remote_repository_exists returns False when repository doesn't exist."""
        provider = BitbucketProvider("test_account")

        with patch.object(provider, "_get_versioner") as mock_get_versioner:
            mock_versioner = MagicMock()

            # Create an async mock for check_remote_repository_exists
            async def async_check_remote_repository_exists(_url):
                return False

            mock_versioner.check_remote_repository_exists = (
                async_check_remote_repository_exists
            )
            mock_get_versioner.return_value = mock_versioner

            result = await provider.check_remote_repository_exists("test_repo")

            assert result is False
            mock_get_versioner.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_remote_repository_exists_exception(self) -> None:
        """Test check_remote_repository_exists returns False when exception occurs."""
        provider = BitbucketProvider("test_account")

        with patch.object(provider, "_get_versioner") as mock_get_versioner:
            mock_versioner = MagicMock()

            # Create an async mock for check_remote_repository_exists that raises an exception
            async def async_check_remote_repository_exists(_url):
                error_msg = "Network error"
                raise RuntimeError(error_msg)

            mock_versioner.check_remote_repository_exists = (
                async_check_remote_repository_exists
            )
            mock_get_versioner.return_value = mock_versioner

            result = await provider.check_remote_repository_exists("test_repo")

            assert result is False
            mock_get_versioner.assert_called_once()

    def test_docstring_contains_expected_content(self) -> None:
        """Test that the class docstring contains expected content."""
        docstring = BitbucketProvider.__doc__
        assert "Provider for Bitbucket repository operations" in docstring
        assert "account_name" in docstring
        assert "auth" in docstring

    def test_get_branch_returns_empty_before_clone(self) -> None:
        """Test get_branch returns empty string before clone."""
        provider = BitbucketProvider("test_account")
        # Before clone, branch_used is None, so should return empty string
        assert provider.get_branch() == ""

    @pytest.mark.asyncio
    @patch(
        "kbot_installer.core.provider.bitbucket_provider.GitMixin.clone_and_checkout"
    )
    async def test_get_branch_returns_used_branch_after_clone(
        self, mock_clone_and_checkout
    ) -> None:
        """Test get_branch returns the branch used during clone."""
        provider = BitbucketProvider("test_account")

        # Mock the parent clone to simulate setting branch_used
        async def mock_clone(url, path, branch):
            provider.branch_used = branch

        mock_clone_and_checkout.side_effect = mock_clone

        await provider.clone_and_checkout("test_repo", "/test/path", "develop")

        # After clone with branch "develop", should return "develop"
        assert provider.get_branch() == "develop"

    @pytest.mark.asyncio
    @patch(
        "kbot_installer.core.provider.bitbucket_provider.GitMixin.clone_and_checkout"
    )
    async def test_get_branch_returns_empty_when_no_branch(
        self, mock_clone_and_checkout
    ) -> None:
        """Test get_branch returns empty string when no branch specified."""
        provider = BitbucketProvider("test_account")

        # Mock the parent clone to simulate setting branch_used to None
        async def mock_clone(url, path, branch):
            provider.branch_used = None

        mock_clone_and_checkout.side_effect = mock_clone

        await provider.clone_and_checkout("test_repo", "/test/path", None)

        # When None is specified, should return empty string
        assert provider.get_branch() == ""
