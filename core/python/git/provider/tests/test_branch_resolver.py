"""Tests for the branch_resolver module."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from git.provider.base import ProviderBase
from git.provider.branch_resolver import (
    clone_with_branch_fallback,
    get_branches_to_try,
)
from git.provider.errors import ProviderError


class TestGetBranchesToTry:
    """Test cases for get_branches_to_try."""

    def test_explicit_branch_keeps_configured_fallbacks(self) -> None:
        """Test explicit branch keeps configured provider fallbacks."""
        assert get_branches_to_try(["main", "dev"], "master") == [
            "master",
            "main",
            "dev",
        ]

    def test_default_uses_configured_branches(self) -> None:
        """Test missing branch uses the provider's configured branches."""
        assert get_branches_to_try(["main", "dev"], None) == ["main", "dev"]

    def test_explicit_branch_deduplicates(self) -> None:
        """Test explicit branch is not duplicated when already configured."""
        assert get_branches_to_try(["master", "dev"], "master") == [
            "master",
            "dev",
        ]

    def test_no_configured_branches_returns_requested_branch_only(self) -> None:
        """Test that a provider without configured fallback branches is handled safely."""
        assert get_branches_to_try([], "master") == ["master"]
        assert get_branches_to_try([], None) == []


class TestCloneWithBranchFallback:
    """Test cases for clone_with_branch_fallback."""

    def test_tries_first_branch_that_succeeds(self) -> None:
        """Test that the fallback stops at the first branch that succeeds."""
        provider = MagicMock(spec=ProviderBase)

        branch_used = clone_with_branch_fallback(
            provider,
            "test-repo",
            Path("/tmp/test"),
            ["main", "master"],
            commit_id=None,
        )

        assert branch_used == "main"
        provider.clone_and_checkout.assert_called_once_with(
            "test-repo", Path("/tmp/test"), branch="main", commit_id=None
        )

    def test_falls_back_on_branch_not_found(self) -> None:
        """Test that the fallback retries the next branch on a not-found error."""
        provider = MagicMock(spec=ProviderBase)
        provider.clone_and_checkout.side_effect = [
            ProviderError("Version 'main' not found"),
            None,
        ]

        branch_used = clone_with_branch_fallback(
            provider,
            "test-repo",
            Path("/tmp/test"),
            ["main", "master"],
        )

        assert branch_used == "master"
        assert provider.clone_and_checkout.call_count == 2

    def test_raises_immediately_on_unrelated_error(self) -> None:
        """Test that a non-branch-related error is not retried with the next branch."""
        provider = MagicMock(spec=ProviderBase)
        provider.clone_and_checkout.side_effect = ProviderError("Connection refused")

        with pytest.raises(ProviderError, match="Connection refused"):
            clone_with_branch_fallback(
                provider,
                "test-repo",
                Path("/tmp/test"),
                ["main", "master"],
            )

        provider.clone_and_checkout.assert_called_once()

    def test_raises_last_error_when_every_branch_fails(self) -> None:
        """Test that the last branch's error propagates when all branches fail."""
        provider = MagicMock(spec=ProviderBase)
        provider.clone_and_checkout.side_effect = ProviderError(
            "Version 'master' not found"
        )

        with pytest.raises(ProviderError, match="Version 'master' not found"):
            clone_with_branch_fallback(
                provider,
                "test-repo",
                Path("/tmp/test"),
                ["main", "master"],
            )

        assert provider.clone_and_checkout.call_count == 2

    def test_empty_branch_list_clones_without_a_branch(self) -> None:
        """Test that an empty branch list falls back to a plain clone."""
        provider = MagicMock(spec=ProviderBase)

        branch_used = clone_with_branch_fallback(
            provider,
            "test-repo",
            Path("/tmp/test"),
            [],
            commit_id="deadbeef",
        )

        assert branch_used == ""
        provider.clone_and_checkout.assert_called_once_with(
            "test-repo", Path("/tmp/test"), commit_id="deadbeef"
        )
