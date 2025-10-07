"""Tests for GitMixin error message improvements."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from kbot_installer.core.provider.git_mixin import GitMixin
from kbot_installer.core.provider.provider_base import ProviderError
from kbot_installer.core.versioner.versioner_base import VersionerError


class TestGitMixinErrorMessages:
    """Test cases for improved error messages in GitMixin."""

    @pytest.mark.asyncio
    async def test_clone_and_checkout_branch_not_found_error(self) -> None:
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
        mock_versioner.clone = AsyncMock()
        mock_versioner.checkout = AsyncMock()

        # Mock checkout to raise a branch not found error
        mock_versioner.checkout.side_effect = VersionerError(
            "Version 'release-2021.03-dev' not found. Available versions: dev, master, release-2025.03"
        )

        with patch.object(provider, "_get_versioner", return_value=mock_versioner):
            with pytest.raises(ProviderError) as exc_info:
                await provider.clone_and_checkout(
                    "test-repo", "/tmp/test", "release-2021.03-dev"
                )

            # Check that the error message is specific to version not found
            error_msg = str(exc_info.value)
            assert "Version 'release-2021.03-dev' not found" in error_msg
            assert "test-repo" in error_msg
            assert "Available versions" in error_msg

    @pytest.mark.asyncio
    async def test_clone_and_checkout_generic_checkout_error(self) -> None:
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
        mock_versioner.clone = AsyncMock()
        mock_versioner.checkout = AsyncMock()

        # Mock checkout to raise a generic checkout error
        mock_versioner.checkout.side_effect = VersionerError(
            "Failed to checkout due to file conflicts"
        )

        with patch.object(provider, "_get_versioner", return_value=mock_versioner):
            with pytest.raises(ProviderError) as exc_info:
                await provider.clone_and_checkout(
                    "test-repo", "/tmp/test", "release-2021.03-dev"
                )

            # Check that the error message is about checkout failure
            error_msg = str(exc_info.value)
            assert "Failed to checkout branch 'release-2021.03-dev'" in error_msg
            assert "test-repo" in error_msg

    @pytest.mark.asyncio
    async def test_clone_and_checkout_clone_error(self) -> None:
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
        mock_versioner.clone = AsyncMock()

        # Mock clone to raise an error
        mock_versioner.clone.side_effect = VersionerError("Repository not found")

        with patch.object(provider, "_get_versioner", return_value=mock_versioner):
            with pytest.raises(ProviderError) as exc_info:
                await provider.clone_and_checkout(
                    "test-repo", "/tmp/test", "release-2021.03-dev"
                )

            # Check that the error message is about clone failure
            error_msg = str(exc_info.value)
            assert "Failed to clone repository 'test-repo'" in error_msg

    @pytest.mark.asyncio
    async def test_clone_and_checkout_success(self) -> None:
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
        mock_versioner.clone = AsyncMock()
        mock_versioner.checkout = AsyncMock()

        with patch.object(provider, "_get_versioner", return_value=mock_versioner):
            # Should not raise any exception
            await provider.clone_and_checkout(
                "test-repo", "/tmp/test", "release-2021.03-dev"
            )

            # Verify both methods were called
            mock_versioner.clone.assert_called_once_with("test-repo", "/tmp/test")
            mock_versioner.checkout.assert_called_once_with(
                "/tmp/test", "release-2021.03-dev"
            )

    @pytest.mark.asyncio
    async def test_clone_and_checkout_without_branch(self) -> None:
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
        mock_versioner.clone = AsyncMock()

        with patch.object(provider, "_get_versioner", return_value=mock_versioner):
            # Should not raise any exception
            await provider.clone_and_checkout("test-repo", "/tmp/test", None)

            # Verify only clone was called
            mock_versioner.clone.assert_called_once_with("test-repo", "/tmp/test")
            mock_versioner.checkout.assert_not_called()
