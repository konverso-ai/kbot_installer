"""Tests for the git_provider_base module."""

from unittest.mock import MagicMock, patch

import pytest

from git.provider.errors import ProviderError
from git.provider.git_provider_base import GitProviderBase
from git.versioner import VersionerError


class ConcreteProvider(GitProviderBase):
    """Concrete provider for testing GitProviderBase."""

    name = "concrete"
    ssh_host = "concrete.example.com"
    base_url = "https://{name}.example.com/{account_name}/{repository_name}.git"


class TestGitProviderBase:
    """Test cases for GitProviderBase class."""

    def test_can_be_instantiated_with_concrete_implementation(self) -> None:
        """Test that GitProviderBase can be instantiated with a subclass."""
        provider = ConcreteProvider("acme")
        assert isinstance(provider, GitProviderBase)

    def test_accepts_injected_versioner(self) -> None:
        """Test that a pre-built versioner can be injected via the constructor."""
        mock_versioner = MagicMock()
        provider = ConcreteProvider("acme", versioner=mock_versioner)

        assert provider._get_versioner() is mock_versioner

    def test_get_versioner_creates_versioner_once(self) -> None:
        """Test that _get_versioner creates a versioner only once, lazily."""
        provider = ConcreteProvider("acme")

        with patch("git.provider.git_provider_base.add_versioner") as mock_create:
            mock_versioner = MagicMock()
            mock_create.return_value = mock_versioner

            result1 = provider._get_versioner()
            result2 = provider._get_versioner()

            mock_create.assert_called_once()
            assert result1 is result2
            assert result1 is mock_versioner

    def test_get_auth_returns_none_by_default(self) -> None:
        """Test that _get_auth returns None when no auth was configured."""
        provider = ConcreteProvider("acme")
        assert provider._get_auth() is None

    def test_get_auth_returns_configured_auth(self) -> None:
        """Test that _get_auth returns the auth object passed at construction."""
        mock_auth = MagicMock()
        provider = ConcreteProvider("acme", auth=mock_auth)
        assert provider._get_auth() is mock_auth

    def test_clone_and_checkout_calls_versioner(self) -> None:
        """Test that clone_and_checkout calls the versioner."""
        mock_versioner = MagicMock()
        provider = ConcreteProvider("acme", versioner=mock_versioner)

        provider.clone_and_checkout(
            "/test/path", "main", repository_url="https://test.com/repo"
        )

        mock_versioner.clone.assert_called_once_with(
            "https://test.com/repo",
            "/test/path",
            branch="main",
            depth=1,
        )
        mock_versioner.checkout.assert_not_called()
        assert provider.get_branch() == "main"

    def test_clone_and_checkout_without_branch(self) -> None:
        """Test clone without checkout when no branch is requested."""
        mock_versioner = MagicMock()
        provider = ConcreteProvider("acme", versioner=mock_versioner)

        provider.clone_and_checkout("/test/path", repository_url="test-repo")

        mock_versioner.clone.assert_called_once_with("test-repo", "/test/path")
        assert provider.get_branch() == ""

    def test_clone_and_checkout_builds_url_from_repository_name(self) -> None:
        """Test that repository_name is resolved into a repository URL."""
        mock_versioner = MagicMock()
        provider = ConcreteProvider("acme", versioner=mock_versioner)

        provider.clone_and_checkout(
            "/test/path", "main", repository_name="test_repo"
        )

        mock_versioner.clone.assert_called_once_with(
            "https://concrete.example.com/acme/test_repo.git",
            "/test/path",
            branch="main",
            depth=1,
        )

    def test_clone_and_checkout_requires_url_or_name(self) -> None:
        """Test that clone_and_checkout requires a URL or a repository name."""
        provider = ConcreteProvider("acme", versioner=MagicMock())

        with pytest.raises(ValueError, match="repository_url or repository_name"):
            provider.clone_and_checkout("/test/path")

    def test_clone_and_checkout_handles_versioner_error(self) -> None:
        """Test that clone_and_checkout wraps VersionerError in ProviderError."""
        mock_versioner = MagicMock()
        mock_versioner.clone.side_effect = VersionerError("Test error")
        provider = ConcreteProvider("acme", versioner=mock_versioner)

        with pytest.raises(ProviderError, match="Failed to clone repository"):
            provider.clone_and_checkout(
                "/test/path", "main", repository_url="https://test.com/repo"
            )

    def test_clone_and_checkout_branch_not_found_error_message(self) -> None:
        """Test that the branch-not-found detail from the versioner is preserved."""
        mock_versioner = MagicMock()
        mock_versioner.clone.side_effect = VersionerError(
            "Version 'release-2021.03-dev' not found. "
            "Available versions: dev, master, release-2025.03"
        )
        provider = ConcreteProvider("acme", versioner=mock_versioner)

        with pytest.raises(ProviderError) as exc_info:
            provider.clone_and_checkout(
                "/tmp/test", "release-2021.03-dev", repository_url="test-repo"
            )

        error_msg = str(exc_info.value)
        assert "Failed to clone repository 'test-repo'" in error_msg
        assert "release-2021.03-dev" in error_msg

    def test_list_remote_branches_delegates_to_versioner(self) -> None:
        """Test that list_remote_branches delegates to the versioner."""
        mock_versioner = MagicMock()
        mock_versioner.list_remote_branches.return_value = ["main", "develop"]
        provider = ConcreteProvider("acme", versioner=mock_versioner)

        assert provider.list_remote_branches("https://test.com/repo") == [
            "main",
            "develop",
        ]

    def test_list_remote_branches_wraps_versioner_error(self) -> None:
        """Test that list_remote_branches wraps VersionerError in ProviderError."""
        mock_versioner = MagicMock()
        mock_versioner.list_remote_branches.side_effect = VersionerError("boom")
        provider = ConcreteProvider("acme", versioner=mock_versioner)

        with pytest.raises(ProviderError, match="Failed to list remote branches"):
            provider.list_remote_branches("https://test.com/repo")

    def test_checkout_branch_delegates_to_versioner(self) -> None:
        """Test that checkout_branch delegates to the versioner and stores the branch."""
        mock_versioner = MagicMock()
        provider = ConcreteProvider("acme", versioner=mock_versioner)

        provider.checkout_branch("/test/path", "develop")

        mock_versioner.checkout.assert_called_once_with("/test/path", "develop")
        assert provider.get_branch() == "develop"

    def test_checkout_branch_wraps_versioner_error(self) -> None:
        """Test that checkout_branch wraps VersionerError in ProviderError."""
        mock_versioner = MagicMock()
        mock_versioner.checkout.side_effect = VersionerError("boom")
        provider = ConcreteProvider("acme", versioner=mock_versioner)

        with pytest.raises(ProviderError, match="Failed to checkout branch"):
            provider.checkout_branch("/test/path", "develop")

    def test_check_remote_repository_exists_true(self) -> None:
        """Test check_remote_repository_exists returns True when the remote exists."""
        mock_versioner = MagicMock()
        mock_versioner.remote_exists.return_value = True
        provider = ConcreteProvider("acme", versioner=mock_versioner)

        assert provider.check_remote_repository_exists("test_repo") is True

    def test_check_remote_repository_exists_false_on_exception(self) -> None:
        """Test check_remote_repository_exists returns False on any exception."""
        mock_versioner = MagicMock()
        mock_versioner.remote_exists.side_effect = RuntimeError("network error")
        provider = ConcreteProvider("acme", versioner=mock_versioner)

        assert provider.check_remote_repository_exists("test_repo") is False

    def test_get_name_returns_class_name(self) -> None:
        """Test that get_name returns the provider's configured name."""
        provider = ConcreteProvider("acme")
        assert provider.get_name() == "concrete"

    def test_get_branch_returns_empty_before_any_operation(self) -> None:
        """Test get_branch returns empty string before any clone/checkout."""
        provider = ConcreteProvider("acme")
        assert provider.get_branch() == ""
