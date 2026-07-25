"""Tests for github_provider module."""

from unittest.mock import MagicMock, patch

from git.auth_protocol import GitAuthProtocol
from git.provider.base import ProviderBase
from git.provider.git_provider_base import GitProviderBase
from git.provider.github_provider import GithubProvider


class TestGithubProvider:
    """Test cases for GithubProvider class."""

    def test_inherits_from_provider_base(self) -> None:
        """Test that GithubProvider inherits from ProviderBase."""
        assert issubclass(GithubProvider, ProviderBase)
        assert issubclass(GithubProvider, GitProviderBase)

    def test_initialization_with_auth(self) -> None:
        """Test proper initialization of GithubProvider with authentication."""
        mock_auth = MagicMock(spec=GitAuthProtocol)
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

    def test_initialization_handles_empty_account_name(self) -> None:
        """Test that initialization handles empty account_name."""
        provider = GithubProvider("")
        assert provider.account_name == ""
        assert provider._auth is None

    def test_initialization_with_injected_versioner(self) -> None:
        """Test that a pre-built versioner can be injected via the constructor."""
        mock_versioner = MagicMock()
        provider = GithubProvider("test_account", versioner=mock_versioner)

        assert provider._get_versioner() is mock_versioner

    def test_get_auth_with_auth(self) -> None:
        """Test that _get_auth returns the authentication object when provided."""
        mock_auth = MagicMock(spec=GitAuthProtocol)
        provider = GithubProvider("test_account", mock_auth)

        assert provider._get_auth() == mock_auth

    def test_get_auth_without_auth(self) -> None:
        """Test that _get_auth returns None when no authentication is provided."""
        provider = GithubProvider("test_account")

        assert provider._get_auth() is None

    def test_clone_and_checkout_uses_ssh_url_with_ssh_auth(self) -> None:
        """Test that SSH auth uses a git@ repository URL."""
        from auth.ssh.factory import add_ssh_auth

        mock_versioner = MagicMock()
        provider = GithubProvider(
            "test_account", add_ssh_auth("ssh", username="git"), mock_versioner
        )
        provider.clone_and_checkout("/test/path", "main", repository_name="test_repo")

        mock_versioner.clone.assert_called_once_with(
            "git@github.com:test_account/test_repo.git",
            "/test/path",
            branch="main",
            depth=1,
        )

    def test_clone_and_checkout_builds_https_url(self) -> None:
        """Test that clone_and_checkout builds the expected HTTPS URL."""
        mock_versioner = MagicMock()
        provider = GithubProvider("test_account", versioner=mock_versioner)
        provider.clone_and_checkout("/test/path", "main", repository_name="test_repo")

        mock_versioner.clone.assert_called_once_with(
            "https://github.com/test_account/test_repo.git",
            "/test/path",
            branch="main",
            depth=1,
        )

    def test_clone_and_checkout_without_branch(self) -> None:
        """Test that clone_and_checkout works without specifying branch."""
        mock_versioner = MagicMock()
        provider = GithubProvider("test_account", versioner=mock_versioner)
        provider.clone_and_checkout("/test/path", repository_name="test_repo")

        mock_versioner.clone.assert_called_once_with(
            "https://github.com/test_account/test_repo.git", "/test/path"
        )

    def test_clone_and_checkout_with_different_branch(self) -> None:
        """Test that clone_and_checkout works with different branch."""
        mock_versioner = MagicMock()
        provider = GithubProvider("test_account", versioner=mock_versioner)
        provider.clone_and_checkout(
            "/test/path", "develop", repository_name="test_repo"
        )

        mock_versioner.clone.assert_called_once_with(
            "https://github.com/test_account/test_repo.git",
            "/test/path",
            branch="develop",
            depth=1,
        )

    def test_check_remote_repository_exists_success(self) -> None:
        """Test check_remote_repository_exists returns True when repository exists."""
        provider = GithubProvider("test_account")

        with patch.object(provider, "_get_versioner") as mock_get_versioner:
            mock_versioner = MagicMock()
            mock_versioner.remote_exists.return_value = True
            mock_get_versioner.return_value = mock_versioner

            result = provider.check_remote_repository_exists("test_repo")

            assert result is True

    def test_check_remote_repository_exists_failure(self) -> None:
        """Test check_remote_repository_exists returns False when repository doesn't exist."""
        provider = GithubProvider("test_account")

        with patch.object(provider, "_get_versioner") as mock_get_versioner:
            mock_versioner = MagicMock()
            mock_versioner.remote_exists.return_value = False
            mock_get_versioner.return_value = mock_versioner

            result = provider.check_remote_repository_exists("test_repo")

            assert result is False

    def test_check_remote_repository_exists_exception(self) -> None:
        """Test check_remote_repository_exists returns False when exception occurs."""
        provider = GithubProvider("test_account")

        with patch.object(provider, "_get_versioner") as mock_get_versioner:
            mock_versioner = MagicMock()
            mock_versioner.remote_exists.side_effect = RuntimeError("Network error")
            mock_get_versioner.return_value = mock_versioner

            result = provider.check_remote_repository_exists("test_repo")

            assert result is False

    def test_docstring_contains_expected_content(self) -> None:
        """Test that the class docstring contains expected content."""
        docstring = GithubProvider.__doc__
        assert "Provider for GitHub repository operations" in docstring
        assert "account_name" in docstring
        assert "auth" in docstring

    def test_get_branch_returns_empty_before_clone(self) -> None:
        """Test get_branch returns empty string before clone."""
        provider = GithubProvider("test_account")
        assert provider.get_branch() == ""

    def test_get_branch_returns_used_branch_after_clone(self) -> None:
        """Test get_branch returns the branch used during clone."""
        mock_versioner = MagicMock()
        provider = GithubProvider("test_account", versioner=mock_versioner)

        provider.clone_and_checkout(
            "/test/path", "develop", repository_name="test_repo"
        )

        assert provider.get_branch() == "develop"

    def test_get_branch_returns_empty_when_no_branch(self) -> None:
        """Test get_branch returns empty string when no branch specified."""
        mock_versioner = MagicMock()
        provider = GithubProvider("test_account", versioner=mock_versioner)

        provider.clone_and_checkout("/test/path", None, repository_name="test_repo")

        assert provider.get_branch() == ""
