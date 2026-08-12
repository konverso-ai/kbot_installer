"""Tests for bitbucket_provider module."""

from unittest.mock import MagicMock

from auth.ssh.ssh_auth import SshAuth
from git.provider.base import ProviderBase
from git.provider.bitbucket_provider import BitbucketProvider
from git.provider.provider_mixin import ProviderMixin


class TestBitbucketProvider:
    """Test cases for BitbucketProvider class."""

    def test_inherits_from_provider_mixin(self) -> None:
        """Test that BitbucketProvider inherits from ProviderBase via ProviderMixin."""
        assert issubclass(BitbucketProvider, ProviderBase)
        assert issubclass(BitbucketProvider, ProviderMixin)

    def test_configures_expected_class_attributes(self) -> None:
        """Test that BitbucketProvider only sets its Bitbucket-specific attributes."""
        assert BitbucketProvider.name == "bitbucket"
        assert BitbucketProvider.ssh_host == "bitbucket.org"
        assert (
            BitbucketProvider.base_url
            == "https://{name}.org/{account_name}/{repository_name}.git"
        )

    def test_initialization(self) -> None:
        """Test proper initialization of BitbucketProvider with account and versioner."""
        mock_versioner = MagicMock()
        provider = BitbucketProvider("test_account", versioner=mock_versioner)

        assert provider.account_name == "test_account"
        assert provider.get_name() == "bitbucket"

    def test_clone_and_checkout_uses_ssh_url_with_ssh_auth(self) -> None:
        """Test that SSH auth uses a git@ repository URL."""
        mock_versioner = MagicMock()
        mock_versioner._get_auth.return_value = MagicMock(spec=SshAuth)
        provider = BitbucketProvider("test_account", versioner=mock_versioner)

        provider.clone_and_checkout("test_repo", "/test/path", branch="main")

        mock_versioner.clone.assert_called_once_with(
            "git@bitbucket.org:test_account/test_repo.git",
            "/test/path",
        )
        mock_versioner.checkout.assert_called_once_with("/test/path", "main")

    def test_clone_and_checkout_builds_https_url(self) -> None:
        """Test that clone_and_checkout builds the expected HTTPS URL."""
        mock_versioner = MagicMock()
        mock_versioner._get_auth.return_value = None
        provider = BitbucketProvider("test_account", versioner=mock_versioner)

        provider.clone_and_checkout("test_repo", "/test/path", branch="main")

        mock_versioner.clone.assert_called_once_with(
            "https://bitbucket.org/test_account/test_repo.git",
            "/test/path",
        )
        mock_versioner.checkout.assert_called_once_with("/test/path", "main")

    def test_clone_and_checkout_without_branch(self) -> None:
        """Test that clone_and_checkout works without specifying a branch."""
        mock_versioner = MagicMock()
        mock_versioner._get_auth.return_value = None
        provider = BitbucketProvider("test_account", versioner=mock_versioner)

        provider.clone_and_checkout("test_repo", "/test/path")

        mock_versioner.clone.assert_called_once_with(
            "https://bitbucket.org/test_account/test_repo.git", "/test/path"
        )

    def test_remote_exists_success(self) -> None:
        """Test remote_exists returns True when the repository exists."""
        mock_versioner = MagicMock()
        mock_versioner._get_auth.return_value = None
        mock_versioner.remote_exists.return_value = True
        provider = BitbucketProvider("test_account", versioner=mock_versioner)

        assert provider.remote_exists("test_repo") is True

    def test_remote_exists_failure(self) -> None:
        """Test remote_exists returns False when the repository doesn't exist."""
        mock_versioner = MagicMock()
        mock_versioner._get_auth.return_value = None
        mock_versioner.remote_exists.return_value = False
        provider = BitbucketProvider("test_account", versioner=mock_versioner)

        assert provider.remote_exists("test_repo") is False

    def test_remote_exists_exception(self) -> None:
        """Test remote_exists returns False when an exception occurs."""
        mock_versioner = MagicMock()
        mock_versioner._get_auth.return_value = None
        mock_versioner.remote_exists.side_effect = RuntimeError("Network error")
        provider = BitbucketProvider("test_account", versioner=mock_versioner)

        assert provider.remote_exists("test_repo") is False

    def test_get_branch_returns_empty_before_clone(self) -> None:
        """Test get_branch returns empty string before clone."""
        provider = BitbucketProvider("test_account", versioner=MagicMock())
        assert provider.get_branch() == ""

    def test_get_branch_returns_used_branch_after_clone(self) -> None:
        """Test get_branch returns the branch used during clone."""
        mock_versioner = MagicMock()
        mock_versioner._get_auth.return_value = None
        provider = BitbucketProvider("test_account", versioner=mock_versioner)

        provider.clone_and_checkout("test_repo", "/test/path", branch="develop")

        assert provider.get_branch() == "develop"

    def test_get_branch_returns_empty_when_no_branch(self) -> None:
        """Test get_branch returns empty string when no branch specified."""
        mock_versioner = MagicMock()
        mock_versioner._get_auth.return_value = None
        provider = BitbucketProvider("test_account", versioner=mock_versioner)

        provider.clone_and_checkout("test_repo", "/test/path")

        assert provider.get_branch() == ""
