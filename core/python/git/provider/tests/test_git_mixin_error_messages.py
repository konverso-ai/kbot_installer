"""Tests for GitMixin error message improvements."""

from unittest.mock import MagicMock, patch

import pytest

from git.provider.git_mixin import GitMixin
from git.provider.errors import ProviderError
from git.versioner.base import VersionerError


class TestGitMixinErrorMessages:
    """Test cases for improved error messages in GitMixin."""

    def test_clone_and_checkout_branch_not_found_error(self) -> None:
        """Test that branch not found errors are properly distinguished."""

        # Create a concrete implementation of GitMixin
        class TestProvider(GitMixin):
            def _get_auth(self):
                return None

            def check_remote_repository_exists(self, repository_url: str) -> bool:
                return True

            def get_name(self) -> str:
                return "test"

        provider = TestProvider()

        # Mock versioner
        mock_versioner = MagicMock()
        mock_versioner.clone = MagicMock(
            side_effect=VersionerError(
                "Version 'release-2021.03-dev' not found. "
                "Available versions: dev, master, release-2025.03"
            )
        )

        with patch.object(provider, "_get_versioner", return_value=mock_versioner):
            with pytest.raises(ProviderError) as exc_info:
                provider.clone_and_checkout(
                    "/tmp/test",
                    "release-2021.03-dev",
                    repository_url="test-repo",
                )

            error_msg = str(exc_info.value)
            assert "Failed to clone repository 'test-repo'" in error_msg
            assert "release-2021.03-dev" in error_msg
            mock_versioner.clone.assert_called_once_with(
                "test-repo",
                "/tmp/test",
                branch="release-2021.03-dev",
                depth=1,
            )

    def test_clone_and_checkout_generic_checkout_error(self) -> None:
        """Test that generic checkout errors are handled properly."""

        # Create a concrete implementation of GitMixin
        class TestProvider(GitMixin):
            def _get_auth(self):
                return None

            def check_remote_repository_exists(self, repository_url: str) -> bool:
                return True

            def get_name(self) -> str:
                return "test"

        provider = TestProvider()

        # Mock versioner
        mock_versioner = MagicMock()
        mock_versioner.clone = MagicMock(
            side_effect=VersionerError("Failed to checkout due to file conflicts")
        )

        with patch.object(provider, "_get_versioner", return_value=mock_versioner):
            with pytest.raises(ProviderError) as exc_info:
                provider.clone_and_checkout(
                    "/tmp/test",
                    "release-2021.03-dev",
                    repository_url="test-repo",
                )

            error_msg = str(exc_info.value)
            assert "Failed to clone repository 'test-repo'" in error_msg

    def test_clone_and_checkout_clone_error(self) -> None:
        """Test that clone errors are handled properly."""

        # Create a concrete implementation of GitMixin
        class TestProvider(GitMixin):
            def _get_auth(self):
                return None

            def check_remote_repository_exists(self, repository_url: str) -> bool:
                return True

            def get_name(self) -> str:
                return "test"

        provider = TestProvider()

        # Mock versioner
        mock_versioner = MagicMock()
        mock_versioner.clone = MagicMock()

        # Mock clone to raise an error
        mock_versioner.clone.side_effect = VersionerError("Repository not found")

        with patch.object(provider, "_get_versioner", return_value=mock_versioner):
            with pytest.raises(ProviderError) as exc_info:
                provider.clone_and_checkout(
                    "/tmp/test",
                    "release-2021.03-dev",
                    repository_url="test-repo",
                )

            # Check that the error message is about clone failure
            error_msg = str(exc_info.value)
            assert "Failed to clone repository 'test-repo'" in error_msg

    def test_clone_and_checkout_success(self) -> None:
        """Test successful clone and checkout."""

        # Create a concrete implementation of GitMixin
        class TestProvider(GitMixin):
            def _get_auth(self):
                return None

            def check_remote_repository_exists(self, repository_url: str) -> bool:
                return True

            def get_name(self) -> str:
                return "test"

        provider = TestProvider()

        # Mock versioner
        mock_versioner = MagicMock()
        mock_versioner.clone = MagicMock()
        mock_versioner.checkout = MagicMock()

        with patch.object(provider, "_get_versioner", return_value=mock_versioner):
            provider.clone_and_checkout(
                "/tmp/test",
                "release-2021.03-dev",
                repository_url="test-repo",
            )

            mock_versioner.clone.assert_called_once_with(
                "test-repo",
                "/tmp/test",
                branch="release-2021.03-dev",
                depth=1,
            )
            mock_versioner.checkout.assert_not_called()

    def test_clone_and_checkout_without_branch(self) -> None:
        """Test clone without checkout."""

        # Create a concrete implementation of GitMixin
        class TestProvider(GitMixin):
            def _get_auth(self):
                return None

            def check_remote_repository_exists(self, repository_url: str) -> bool:
                return True

            def get_name(self) -> str:
                return "test"

        provider = TestProvider()

        # Mock versioner
        mock_versioner = MagicMock()
        mock_versioner.clone = MagicMock()

        with patch.object(provider, "_get_versioner", return_value=mock_versioner):
            # Should not raise any exception
            provider.clone_and_checkout("/tmp/test", None, repository_url="test-repo")

            # Verify only clone was called
            mock_versioner.clone.assert_called_once_with("test-repo", "/tmp/test")
            mock_versioner.checkout.assert_not_called()
