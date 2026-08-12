"""Tests for selector_provider module."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from git.provider.base import ProviderBase
from git.provider.errors import ProviderError
from git.provider.selector_provider import SelectorProvider


class TestSelectorProvider:
    """Test cases for SelectorProvider class."""

    def test_initialization(self) -> None:
        """Test SelectorProvider initialization."""
        providers = [MagicMock(spec=ProviderBase), MagicMock(spec=ProviderBase)]
        selector = SelectorProvider(providers)

        assert selector.providers == providers
        assert selector.quiet is False

    def test_initialization_quiet(self) -> None:
        """Test SelectorProvider initialization with quiet=True."""
        selector = SelectorProvider([], quiet=True)

        assert selector.quiet is True

    def test_clone_success_first_provider(self) -> None:
        """Test successful clone with first provider."""
        mock_storage = MagicMock(spec=ProviderBase)
        mock_github = MagicMock(spec=ProviderBase)
        selector = SelectorProvider([mock_storage, mock_github])

        selector.clone_and_checkout("test_repo", "/tmp/test_path", branch="main")

        mock_storage.clone_and_checkout.assert_called_once_with(
            "test_repo",
            Path("/tmp/test_path"),
            branch="main",
            commit_id=None,
        )
        mock_github.clone_and_checkout.assert_not_called()

    def test_clone_success_second_provider(self) -> None:
        """Test successful clone with second provider after first fails."""
        mock_storage = MagicMock(spec=ProviderBase)
        mock_github = MagicMock(spec=ProviderBase)
        mock_storage.clone_and_checkout = MagicMock(side_effect=ProviderError("Storage failed"))
        selector = SelectorProvider([mock_storage, mock_github])

        selector.clone_and_checkout("test_repo", "/tmp/test_path", branch="main")

        mock_storage.clone_and_checkout.assert_called_once_with(
            "test_repo",
            Path("/tmp/test_path"),
            branch="main",
            commit_id=None,
        )
        mock_github.clone_and_checkout.assert_called_once_with(
            "test_repo",
            Path("/tmp/test_path"),
            branch="main",
            commit_id=None,
        )

    def test_clone_all_providers_fail_provider_error(self) -> None:
        """Test clone when all providers fail with ProviderError."""
        mock_storage = MagicMock(spec=ProviderBase)
        mock_github = MagicMock(spec=ProviderBase)
        mock_storage.clone_and_checkout = MagicMock(side_effect=ProviderError("Storage failed"))
        mock_github.clone_and_checkout = MagicMock(side_effect=ProviderError("Github failed"))
        selector = SelectorProvider([mock_storage, mock_github])

        with pytest.raises(ProviderError, match="All providers failed to clone repository"):
            selector.clone_and_checkout("test_repo", "/tmp/test_path", branch="main")

    def test_clone_all_providers_fail_general_exception(self) -> None:
        """Test clone when all providers fail with a general exception."""
        mock_storage = MagicMock(spec=ProviderBase)
        mock_storage.clone_and_checkout = MagicMock(side_effect=Exception("Boom"))
        selector = SelectorProvider([mock_storage])

        with pytest.raises(ProviderError, match="All providers failed to clone repository"):
            selector.clone_and_checkout("test_repo", "/tmp/test_path", branch="main")

    def test_clone_mixed_failures(self) -> None:
        """Test clone with mixed failure types across providers."""
        mock_storage = MagicMock(spec=ProviderBase)
        mock_github = MagicMock(spec=ProviderBase)
        mock_bitbucket = MagicMock(spec=ProviderBase)

        mock_storage.clone_and_checkout = MagicMock(side_effect=ProviderError("Storage failed"))
        mock_github.clone_and_checkout = MagicMock(side_effect=RuntimeError("Github creation failed"))
        mock_bitbucket.clone_and_checkout = MagicMock(side_effect=ProviderError("Bitbucket failed"))

        selector = SelectorProvider([mock_storage, mock_github, mock_bitbucket])

        with pytest.raises(ProviderError, match="All providers failed to clone repository"):
            selector.clone_and_checkout("test_repo", "/tmp/test_path", branch="main")

    def test_clone_with_commit_id(self) -> None:
        """Test clone forwards commit_id to the underlying provider."""
        mock_provider = MagicMock(spec=ProviderBase)
        selector = SelectorProvider([mock_provider])

        selector.clone_and_checkout("test-repo", "/tmp/test", branch="dev", commit_id="deadbeef")

        mock_provider.clone_and_checkout.assert_called_once_with(
            "test-repo", Path("/tmp/test"), branch="dev", commit_id="deadbeef"
        )

    def test_clone_without_branch(self) -> None:
        """Test clone without an explicit branch clones without branch fallback."""
        mock_provider = MagicMock(spec=ProviderBase)
        selector = SelectorProvider([mock_provider])

        selector.clone_and_checkout("test-repo", "/tmp/test")

        mock_provider.clone_and_checkout.assert_called_once_with(
            "test-repo", Path("/tmp/test"), commit_id=None
        )

    def test_str_representation(self) -> None:
        """Test string representation of SelectorProvider."""
        providers = [MagicMock(spec=ProviderBase), MagicMock(spec=ProviderBase)]
        selector = SelectorProvider(providers)
        assert str(selector) == f"SelectorProvider(providers={providers})"

    def test_repr_representation(self) -> None:
        """Test detailed string representation of SelectorProvider."""
        providers = [MagicMock(spec=ProviderBase)]
        selector = SelectorProvider(providers)
        assert repr(selector) == f"SelectorProvider(providers={providers})"

    def test_provider_name_updated_in_clone(self) -> None:
        """Test that self.name is updated after a successful clone."""
        mock_provider = MagicMock(spec=ProviderBase)
        mock_provider.get_name.return_value = "bitbucket"
        selector = SelectorProvider([mock_provider])

        selector.clone_and_checkout("test-repo", "/tmp/test", branch="main")

        assert selector.name == "bitbucket"

    def test_get_branch_returns_empty_before_clone(self) -> None:
        """Test get_branch returns empty string before clone."""
        selector = SelectorProvider([MagicMock(spec=ProviderBase), MagicMock(spec=ProviderBase)])
        assert selector.get_branch() == ""

    def test_get_branch_returns_used_branch_after_clone(self) -> None:
        """Test get_branch returns the branch used during clone."""
        mock_provider = MagicMock(spec=ProviderBase)
        mock_provider.get_name.return_value = "github"
        selector = SelectorProvider([mock_provider])

        selector.clone_and_checkout("test-repo", "/tmp/test", branch="main")

        assert selector.get_branch() == "main"

    def test_remote_exists_true_first_provider(self) -> None:
        """Test remote_exists returns True as soon as a provider confirms it."""
        mock_storage = MagicMock(spec=ProviderBase)
        mock_storage.remote_exists.return_value = True
        mock_github = MagicMock(spec=ProviderBase)
        selector = SelectorProvider([mock_storage, mock_github])

        assert selector.remote_exists("test-repo") is True
        mock_github.remote_exists.assert_not_called()

    def test_remote_exists_false_when_all_fail(self) -> None:
        """Test remote_exists returns False when no provider confirms it."""
        mock_storage = MagicMock(spec=ProviderBase)
        mock_storage.remote_exists.return_value = False
        mock_github = MagicMock(spec=ProviderBase)
        mock_github.remote_exists.return_value = False
        selector = SelectorProvider([mock_storage, mock_github])

        assert selector.remote_exists("test-repo") is False

    def test_clone_falls_back_to_provider_configured_branches(self) -> None:
        """Test that a provider's own fallback branches are tried after the requested one."""
        mock_provider = MagicMock(spec=ProviderBase)
        mock_provider.branches = ["main", "dev"]
        mock_provider.clone_and_checkout.side_effect = [
            ProviderError("Version 'master' not found"),
            None,
        ]
        selector = SelectorProvider([mock_provider])

        selector.clone_and_checkout("test-repo", "/tmp/test", branch="master")

        assert mock_provider.clone_and_checkout.call_count == 2
        mock_provider.clone_and_checkout.assert_called_with(
            "test-repo", Path("/tmp/test"), branch="main", commit_id=None
        )
        assert selector.get_branch() == "main"

    def test_clone_without_branch_uses_provider_configured_branches(self) -> None:
        """Test that provider fallback branches are used when no branch is requested."""
        mock_provider = MagicMock(spec=ProviderBase)
        mock_provider.branches = ["main", "dev"]
        selector = SelectorProvider([mock_provider])

        selector.clone_and_checkout("test-repo", "/tmp/test")

        mock_provider.clone_and_checkout.assert_called_once_with(
            "test-repo", Path("/tmp/test"), branch="main", commit_id=None
        )

    def test_remote_exists_continues_after_exception(self) -> None:
        """Test remote_exists keeps trying other providers after an exception."""
        mock_storage = MagicMock(spec=ProviderBase)
        mock_storage.remote_exists.side_effect = Exception("boom")
        mock_github = MagicMock(spec=ProviderBase)
        mock_github.remote_exists.return_value = True
        selector = SelectorProvider([mock_storage, mock_github])

        assert selector.remote_exists("test-repo") is True
