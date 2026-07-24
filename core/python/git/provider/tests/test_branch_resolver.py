"""Tests for the branch_resolver module."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from git.provider.branch_resolver import (
    clone_with_branch_fallback,
    get_branches_to_try,
)
from git.provider.errors import ProviderError
from git.provider.git_provider_base import GitProviderBase


class ConcreteGitProvider(GitProviderBase):
    """Minimal git provider for branch_resolver tests."""

    name = "concrete"
    ssh_host = "concrete.example.com"
    base_url = "https://{name}.example.com/{account_name}/{repository_name}.git"


class TestGetBranchesToTry:
    """Test cases for get_branches_to_try."""

    def _config_with_branches(self, branches: list[str]) -> MagicMock:
        provider_config = MagicMock(branches=branches)
        config = MagicMock()
        config.get_provider_config.return_value = provider_config
        return config

    def test_explicit_branch_keeps_configured_fallbacks(self) -> None:
        """Test explicit branch keeps configured provider fallbacks."""
        config = self._config_with_branches(["main", "dev"])
        assert get_branches_to_try(config, "github", "master") == [
            "master",
            "main",
            "dev",
        ]

    def test_default_uses_config_branches(self) -> None:
        """Test missing branch uses configured provider branches."""
        config = self._config_with_branches(["main", "dev"])
        assert get_branches_to_try(config, "github", None) == ["main", "dev"]

    def test_explicit_branch_deduplicates(self) -> None:
        """Test explicit branch is not duplicated when already configured."""
        config = self._config_with_branches(["master", "dev"])
        assert get_branches_to_try(config, "bitbucket", "master") == [
            "master",
            "dev",
        ]

    def test_dict_config_returns_requested_branch_only(self) -> None:
        """Test that a plain dict config (used in some tests) is handled safely."""
        assert get_branches_to_try({"github": {}}, "github", "master") == ["master"]
        assert get_branches_to_try({"github": {}}, "github", None) == []


class TestCloneWithBranchFallback:
    """Test cases for clone_with_branch_fallback."""

    def test_git_provider_selects_first_matching_remote_branch(self) -> None:
        """Test that a git provider clones using the first matching remote branch."""
        mock_versioner = MagicMock()
        mock_versioner.list_remote_branches.return_value = ["dev", "master"]
        provider = ConcreteGitProvider("acme", versioner=mock_versioner)

        branch_used = clone_with_branch_fallback(
            provider,
            "test_repo",
            Path("/tmp/test"),
            ["main", "master", "dev"],
            by_url=False,
        )

        assert branch_used == "master"
        mock_versioner.clone.assert_called_once_with(
            "https://concrete.example.com/acme/test_repo.git",
            Path("/tmp/test"),
            branch="master",
            depth=1,
        )

    def test_git_provider_raises_when_no_branch_matches_remote(self) -> None:
        """Test that a git provider raises before cloning if no branch matches."""
        mock_versioner = MagicMock()
        mock_versioner.list_remote_branches.return_value = ["hotfix"]
        provider = ConcreteGitProvider("acme", versioner=mock_versioner)

        with pytest.raises(ProviderError, match="not found on remote repository"):
            clone_with_branch_fallback(
                provider,
                "test_repo",
                Path("/tmp/test"),
                ["main", "dev"],
                by_url=False,
            )

        mock_versioner.clone.assert_not_called()

    def test_generic_provider_tries_first_branch_that_succeeds(self) -> None:
        """Test that a non-git provider stops at the first branch that succeeds."""
        provider = MagicMock()

        branch_used = clone_with_branch_fallback(
            provider,
            "test-repo",
            Path("/tmp/test"),
            ["main", "master"],
            by_url=False,
            commit=None,
        )

        assert branch_used == "main"
        provider.clone_and_checkout.assert_called_once_with(
            Path("/tmp/test"), "main", commit=None, repository_name="test-repo"
        )

    def test_generic_provider_falls_back_on_branch_not_found(self) -> None:
        """Test that a non-git provider retries the next branch on a not-found error."""
        provider = MagicMock()
        provider.clone_and_checkout.side_effect = [
            ProviderError("Version 'main' not found"),
            None,
        ]

        branch_used = clone_with_branch_fallback(
            provider,
            "test-repo",
            Path("/tmp/test"),
            ["main", "master"],
            by_url=False,
        )

        assert branch_used == "master"
        assert provider.clone_and_checkout.call_count == 2

    def test_generic_provider_raises_immediately_on_unrelated_error(self) -> None:
        """Test that a non-branch-related error is not retried with the next branch."""
        provider = MagicMock()
        provider.clone_and_checkout.side_effect = ProviderError("Connection refused")

        with pytest.raises(ProviderError, match="Connection refused"):
            clone_with_branch_fallback(
                provider,
                "test-repo",
                Path("/tmp/test"),
                ["main", "master"],
                by_url=False,
            )

        provider.clone_and_checkout.assert_called_once()
