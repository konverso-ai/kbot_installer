"""Tests for the provider_mixin module."""

from typing import ClassVar
from unittest.mock import MagicMock

import pytest

from auth.ssh.ssh_auth import SshAuth
from git.provider.base import ProviderBase
from git.provider.errors import ProviderError
from git.provider.provider_mixin import ProviderMixin
from git.versioner import VersionerError


class ConcreteProvider(ProviderMixin):
    """Concrete provider for testing ProviderMixin."""

    name = "concrete"
    ssh_host = "concrete.example.com"
    base_url = "https://{name}.example.com/{account_name}/{repository_name}.git"
    default_branches: ClassVar[list[str]] = ["main", "dev"]


def _make_provider(versioner: MagicMock | None = None, branches: list[str] | None = None) -> ConcreteProvider:
    if versioner is None:
        versioner = MagicMock()
        versioner._get_auth.return_value = None
    return ConcreteProvider("acme", versioner=versioner, branches=branches)


class TestProviderMixin:
    """Test cases for the ProviderMixin class."""

    def test_can_be_instantiated_with_concrete_implementation(self) -> None:
        """Test that ProviderMixin can be instantiated with a subclass."""
        provider = _make_provider()
        assert isinstance(provider, ProviderMixin)
        assert isinstance(provider, ProviderBase)

    def test_clone_and_checkout_calls_versioner(self) -> None:
        """Test that clone_and_checkout calls the versioner with a branch."""
        mock_versioner = MagicMock()
        mock_versioner._get_auth.return_value = None
        provider = _make_provider(mock_versioner)

        provider.clone_and_checkout("test_repo", "/test/path", branch="main")

        mock_versioner.clone.assert_called_once_with(
            "https://concrete.example.com/acme/test_repo.git",
            "/test/path",
            branch="main",
            depth=1,
        )
        assert provider.get_branch() == "main"

    def test_clone_and_checkout_without_branch(self) -> None:
        """Test clone without checkout when no branch is requested."""
        mock_versioner = MagicMock()
        mock_versioner._get_auth.return_value = None
        provider = _make_provider(mock_versioner)

        provider.clone_and_checkout("test_repo", "/test/path")

        mock_versioner.clone.assert_called_once_with(
            "https://concrete.example.com/acme/test_repo.git",
            "/test/path",
        )
        assert provider.get_branch() == ""

    def test_clone_and_checkout_ignores_commit_id(self) -> None:
        """Test that commit_id is accepted but has no effect on plain git clones."""
        mock_versioner = MagicMock()
        mock_versioner._get_auth.return_value = None
        provider = _make_provider(mock_versioner)

        provider.clone_and_checkout(
            "test_repo", "/test/path", branch="main", commit_id="deadbeef"
        )

        mock_versioner.clone.assert_called_once_with(
            "https://concrete.example.com/acme/test_repo.git",
            "/test/path",
            branch="main",
            depth=1,
        )

    def test_clone_and_checkout_handles_versioner_error(self) -> None:
        """Test that clone_and_checkout wraps VersionerError in ProviderError."""
        mock_versioner = MagicMock()
        mock_versioner._get_auth.return_value = None
        mock_versioner.clone.side_effect = VersionerError("Test error")
        provider = _make_provider(mock_versioner)

        with pytest.raises(ProviderError, match="Failed to clone repository"):
            provider.clone_and_checkout("test_repo", "/test/path", branch="main")

    def test_clone_and_checkout_branch_not_found_error_message(self) -> None:
        """Test that the branch-not-found detail from the versioner is preserved."""
        mock_versioner = MagicMock()
        mock_versioner._get_auth.return_value = None
        mock_versioner.clone.side_effect = VersionerError(
            "Version 'release-2021.03-dev' not found. "
            "Available versions: dev, master, release-2025.03"
        )
        provider = _make_provider(mock_versioner)

        with pytest.raises(ProviderError) as exc_info:
            provider.clone_and_checkout(
                "test_repo", "/tmp/test", branch="release-2021.03-dev"
            )

        error_msg = str(exc_info.value)
        assert "Failed to clone repository" in error_msg
        assert "release-2021.03-dev" in error_msg

    def test_remote_exists_true(self) -> None:
        """Test remote_exists returns True when the remote exists."""
        mock_versioner = MagicMock()
        mock_versioner._get_auth.return_value = None
        mock_versioner.remote_exists.return_value = True
        provider = _make_provider(mock_versioner)

        assert provider.remote_exists("test_repo") is True

    def test_remote_exists_false_on_exception(self) -> None:
        """Test remote_exists returns False on any exception."""
        mock_versioner = MagicMock()
        mock_versioner._get_auth.return_value = None
        mock_versioner.remote_exists.side_effect = RuntimeError("network error")
        provider = _make_provider(mock_versioner)

        assert provider.remote_exists("test_repo") is False

    def test_build_repository_url_uses_ssh_when_versioner_has_auth(self) -> None:
        """Test that the SSH URL form is used when the versioner reports SSH auth."""
        mock_versioner = MagicMock()
        mock_versioner._get_auth.return_value = MagicMock(spec=SshAuth)
        provider = _make_provider(mock_versioner)

        provider.clone_and_checkout("test_repo", "/test/path")

        mock_versioner.clone.assert_called_once_with(
            "git@concrete.example.com:acme/test_repo.git",
            "/test/path",
        )

    def test_get_name_returns_class_name(self) -> None:
        """Test that get_name returns the provider's configured name."""
        provider = _make_provider()
        assert provider.get_name() == "concrete"

    def test_get_branch_returns_empty_before_any_operation(self) -> None:
        """Test get_branch returns empty string before any clone/checkout."""
        provider = _make_provider()
        assert provider.get_branch() == ""

    def test_branches_defaults_to_class_attribute(self) -> None:
        """Test that self.branches defaults to the class-level fallback branches."""
        provider = _make_provider()
        assert provider.branches == ["main", "dev"]

    def test_branches_can_be_overridden(self) -> None:
        """Test that an explicit branches argument overrides the class default."""
        provider = _make_provider(branches=["release", "stable"])
        assert provider.branches == ["release", "stable"]

    def test_branches_override_does_not_mutate_class_default(self) -> None:
        """Test that mutating an instance's branches list leaves the class default intact."""
        provider = _make_provider(branches=["release"])
        provider.branches.append("extra")
        assert ConcreteProvider.default_branches == ["main", "dev"]
