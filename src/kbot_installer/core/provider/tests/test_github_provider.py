"""Tests for github_provider module."""

from unittest.mock import MagicMock, patch

from kbot_installer.core.auth.pygit_authentication import PyGitAuthenticationBase
from kbot_installer.core.provider.github_provider import GithubProvider
from kbot_installer.core.provider.provider_base import ProviderBase


class TestGithubProvider:
    """Test cases for GithubProvider class."""

    def test_inherits_from_provider_base(self) -> None:
        """Test that GithubProvider inherits from ProviderBase."""
        assert issubclass(GithubProvider, ProviderBase)

    def test_initialization_with_auth(self) -> None:
        """Test proper initialization of GithubProvider with authentication."""
        mock_auth = MagicMock(spec=PyGitAuthenticationBase)
        provider = GithubProvider("test_account", mock_auth)

        assert provider.account_name == "test_account"
        assert provider._auth == mock_auth
        assert (
            provider.base_url
            == "https://{name}.com/{account_name}/{repository_name}.git"
        )

    def test_initialization_without_auth(self) -> None:
        """Test proper initialization of GithubProvider without authentication."""
        provider = GithubProvider("test_account")

        assert provider.account_name == "test_account"
        assert provider._auth is None
        assert (
            provider.base_url
            == "https://{name}.com/{account_name}/{repository_name}.git"
        )

    def test_initialization_handles_empty_account_name(self) -> None:
        """Test that initialization handles empty account_name."""
        provider = GithubProvider("")
        assert provider.account_name == ""
        assert provider._auth is None

    def test_get_auth_with_auth(self) -> None:
        """Test that _get_auth returns the authentication object when provided."""
        mock_auth = MagicMock(spec=PyGitAuthenticationBase)
        provider = GithubProvider("test_account", mock_auth)

        assert provider._get_auth() == mock_auth

    def test_get_auth_without_auth(self) -> None:
        """Test that _get_auth returns None when no authentication is provided."""
        provider = GithubProvider("test_account")

        assert provider._get_auth() is None

    @patch("kbot_installer.core.provider.github_provider.GitMixin.clone_and_checkout")
    def test_clone_and_checkout_calls_parent_clone_and_checkout(
        self, mock_clone_and_checkout
    ) -> None:
        """Test that clone_and_checkout calls the parent clone_and_checkout method."""
        provider = GithubProvider("test_account")
        provider.clone_and_checkout("test_repo", "/test/path", "main")

        mock_clone_and_checkout.assert_called_once_with(
            "https://github.com/test_account/test_repo.git", "/test/path", "main"
        )

    @patch("kbot_installer.core.provider.github_provider.GitMixin.clone_and_checkout")
    def test_clone_and_checkout_without_branch(self, mock_clone_and_checkout) -> None:
        """Test that clone_and_checkout works without specifying branch."""
        provider = GithubProvider("test_account")
        provider.clone_and_checkout("test_repo", "/test/path")

        mock_clone_and_checkout.assert_called_once_with(
            "https://github.com/test_account/test_repo.git", "/test/path", None
        )

    @patch("kbot_installer.core.provider.github_provider.GitMixin.clone_and_checkout")
    def test_clone_and_checkout_with_different_branch(
        self, mock_clone_and_checkout
    ) -> None:
        """Test that clone_and_checkout works with different branch."""
        provider = GithubProvider("test_account")
        provider.clone_and_checkout("test_repo", "/test/path", "develop")

        mock_clone_and_checkout.assert_called_once_with(
            "https://github.com/test_account/test_repo.git", "/test/path", "develop"
        )

    def test_check_remote_repository_exists_success(self) -> None:
        """Test check_remote_repository_exists returns True when repository exists."""
        provider = GithubProvider("test_account")

        with patch.object(provider, "_get_versioner") as mock_get_versioner:
            mock_versioner = MagicMock()
            mock_versioner.check_remote_repository_exists.return_value = True
            mock_get_versioner.return_value = mock_versioner

            result = provider.check_remote_repository_exists("test_repo")

            assert result is True
            mock_get_versioner.assert_called_once()

    def test_check_remote_repository_exists_failure(self) -> None:
        """Test check_remote_repository_exists returns False when repository doesn't exist."""
        provider = GithubProvider("test_account")

        with patch.object(provider, "_get_versioner") as mock_get_versioner:
            mock_versioner = MagicMock()
            mock_versioner.check_remote_repository_exists.return_value = False
            mock_get_versioner.return_value = mock_versioner

            result = provider.check_remote_repository_exists("test_repo")

            assert result is False
            mock_get_versioner.assert_called_once()

    def test_check_remote_repository_exists_exception(self) -> None:
        """Test check_remote_repository_exists returns False when exception occurs."""
        provider = GithubProvider("test_account")

        with patch.object(provider, "_get_versioner") as mock_get_versioner:
            mock_versioner = MagicMock()
            mock_versioner.check_remote_repository_exists.side_effect = RuntimeError(
                "Network error"
            )
            mock_get_versioner.return_value = mock_versioner

            result = provider.check_remote_repository_exists("test_repo")

            assert result is False
            mock_get_versioner.assert_called_once()

    def test_docstring_contains_expected_content(self) -> None:
        """Test that the class docstring contains expected content."""
        docstring = GithubProvider.__doc__
        assert "Provider for GitHub repository operations" in docstring
        assert "account_name" in docstring
        assert "auth" in docstring

    def test_get_branch_returns_empty_before_clone(self) -> None:
        """Test get_branch returns empty string before clone."""
        provider = GithubProvider("test_account")
        # Before clone, branch_used is None, so should return empty string
        assert provider.get_branch() == ""

    @patch("kbot_installer.core.provider.github_provider.GitMixin.clone_and_checkout")
    def test_get_branch_returns_used_branch_after_clone(
        self, mock_clone_and_checkout
    ) -> None:
        """Test get_branch returns the branch used during clone."""
        provider = GithubProvider("test_account")

        # Mock the parent clone to simulate setting branch_used
        def mock_clone(_url, _path, branch):
            provider.branch_used = branch

        mock_clone_and_checkout.side_effect = mock_clone

        provider.clone_and_checkout("test_repo", "/test/path", "develop")

        # After clone with branch "develop", should return "develop"
        assert provider.get_branch() == "develop"

    @patch("kbot_installer.core.provider.github_provider.GitMixin.clone_and_checkout")
    def test_get_branch_returns_empty_when_no_branch(
        self, mock_clone_and_checkout
    ) -> None:
        """Test get_branch returns empty string when no branch specified."""
        provider = GithubProvider("test_account")

        # Mock the parent clone to simulate setting branch_used to None
        def mock_clone(_url, _path, _branch):
            provider.branch_used = None

        mock_clone_and_checkout.side_effect = mock_clone

        provider.clone_and_checkout("test_repo", "/test/path", None)

        # When None is specified, should return empty string
        assert provider.get_branch() == ""
