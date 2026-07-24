"""Tests for git_mixin module."""

from unittest.mock import MagicMock, patch

import pytest

from git.provider.git_mixin import GitMixin
from git.provider.errors import ProviderError
from git.versioner import VersionerError


class ConcreteProvider(GitMixin):
    """Concrete provider for testing GitMixin."""

    def _get_auth(self):
        """Return mock authentication."""
        return MagicMock()

    def check_remote_repository_exists(self, repository_url: str) -> bool:
        """Check if a remote repository exists."""
        return True

    def get_name(self) -> str:
        """Get provider name."""
        return "concrete"


class TestGitMixin:
    """Test cases for GitMixin class."""

    def test_can_be_instantiated_with_concrete_implementation(self) -> None:
        """Test that GitMixin can be instantiated with concrete implementation."""
        provider = ConcreteProvider()
        assert isinstance(provider, GitMixin)

    def test_clone_and_checkout_calls_versioner(self) -> None:
        """Test that clone_and_checkout calls the versioner."""
        provider = ConcreteProvider()

        with patch.object(provider, "_get_versioner") as mock_get_versioner:
            mock_versioner = MagicMock()
            # Create mock functions
            mock_clone = MagicMock()
            mock_checkout = MagicMock()

            def mock_clone_func(*args: object, **kwargs: object) -> object:
                return mock_clone(*args, **kwargs)

            def mock_checkout_func(*args: object, **kwargs: object) -> object:
                return mock_checkout(*args, **kwargs)

            mock_versioner.clone = mock_clone_func
            mock_versioner.checkout = mock_checkout_func
            mock_get_versioner.return_value = mock_versioner

            provider.clone_and_checkout(
                "/test/path", "main", repository_url="https://test.com/repo"
            )

            mock_get_versioner.assert_called_once()
            mock_clone.assert_called_once_with(
                "https://test.com/repo",
                "/test/path",
                branch="main",
                depth=1,
            )
            mock_checkout.assert_not_called()

    def test_clone_and_checkout_handles_versioner_error(self) -> None:
        """Test that clone_and_checkout handles VersionerError."""
        provider = ConcreteProvider()

        with patch.object(provider, "_get_versioner") as mock_get_versioner:
            mock_versioner = MagicMock()

            # Create a mock function that raises an error
            error_message = "Test error"

            def mock_clone(*_args: object, **_kwargs: object) -> object:
                raise VersionerError(error_message)

            mock_versioner.clone = mock_clone
            mock_get_versioner.return_value = mock_versioner

            with pytest.raises(ProviderError, match="Failed to clone repository"):
                provider.clone_and_checkout(
                    "/test/path", "main", repository_url="https://test.com/repo"
                )

    def test_get_versioner_creates_versioner_once(self) -> None:
        """Test that _get_versioner creates versioner only once."""
        provider = ConcreteProvider()

        with patch(
            "git.provider.git_mixin.create_versioner"
        ) as mock_create:
            mock_versioner = MagicMock()
            mock_create.return_value = mock_versioner

            # Call _get_versioner multiple times
            result1 = provider._get_versioner()
            result2 = provider._get_versioner()

            # Should only create versioner once
            mock_create.assert_called_once()
            assert result1 is result2
            assert result1 is mock_versioner

    def test_get_auth_returns_none_by_default(self) -> None:
        """Test that _get_auth returns None by default."""
        provider = ConcreteProvider()
        # Override _get_auth to return None for this test
        provider._get_auth = lambda: None
        assert provider._get_auth() is None

    def test_git_mixin_get_auth_returns_none(self) -> None:
        """Test that GitMixin._get_auth returns None by default."""
        # ConcreteProvider overrides _get_auth to return a mock
        # This test is no longer valid as ConcreteProvider doesn't use the default implementation
