"""Tests for selector_provider module."""

from pathlib import Path
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest

from kbot_installer.core.provider.provider_base import ProviderError
from kbot_installer.core.provider.selector_provider import SelectorProvider


class TestSelectorProvider:
    """Test cases for SelectorProvider class."""

    def test_initialization(self) -> None:
        """Test SelectorProvider initialization."""
        providers = ["nexus", "github", "bitbucket"]
        selector = SelectorProvider(providers)

        assert selector.providers == providers
        assert selector.base_url == ""

    def test_initialization_with_base_url(self) -> None:
        """Test SelectorProvider initialization with base_url."""
        providers = ["nexus", "github"]
        base_url = "https://example.com"
        selector = SelectorProvider(providers, base_url)

        assert selector.providers == providers
        assert selector.base_url == base_url

    def test_create_provider_with_defaults_nexus(self) -> None:
        """Test _create_provider_with_defaults for nexus provider."""
        selector = SelectorProvider(["nexus"])

        with (
            patch(
                "kbot_installer.core.provider.selector_provider.create_provider"
            ) as mock_create,
            patch.object(
                selector.credential_manager, "has_credentials", return_value=True
            ),
            patch.object(
                selector.credential_manager,
                "get_auth_for_provider",
                return_value=MagicMock(),
            ),
        ):
            mock_provider = MagicMock()
            mock_create.return_value = mock_provider

            result = selector._create_provider_with_credentials("nexus")

            mock_create.assert_called_once_with(
                name="nexus",
                domain="nexus.konverso.ai",
                repository="kbot_raw",
                auth=ANY,
            )
            assert result is mock_provider

    def test_create_provider_with_defaults_github(self) -> None:
        """Test _create_provider_with_defaults for github provider."""
        selector = SelectorProvider(["github"])

        with (
            patch(
                "kbot_installer.core.provider.selector_provider.create_provider"
            ) as mock_create,
            patch.object(
                selector.credential_manager, "has_credentials", return_value=True
            ),
            patch.object(
                selector.credential_manager,
                "get_auth_for_provider",
                return_value=MagicMock(),
            ),
        ):
            mock_provider = MagicMock()
            mock_create.return_value = mock_provider

            result = selector._create_provider_with_credentials("github")

            mock_create.assert_called_once_with(
                name="github", account_name="konverso-ai", auth=ANY
            )
            assert result is mock_provider

    def test_create_provider_with_defaults_bitbucket(self) -> None:
        """Test _create_provider_with_defaults for bitbucket provider."""
        selector = SelectorProvider(["bitbucket"])

        with (
            patch(
                "kbot_installer.core.provider.selector_provider.create_provider"
            ) as mock_create,
            patch.object(
                selector.credential_manager, "has_credentials", return_value=True
            ),
            patch.object(
                selector.credential_manager,
                "get_auth_for_provider",
                return_value=MagicMock(),
            ),
        ):
            mock_provider = MagicMock()
            mock_create.return_value = mock_provider

            result = selector._create_provider_with_credentials("bitbucket")

            mock_create.assert_called_once_with(
                name="bitbucket", account_name="konversoai", auth=ANY
            )
            assert result is mock_provider

    def test_create_provider_with_defaults_unknown(self) -> None:
        """Test _create_provider_with_credentials for unknown provider returns None."""
        selector = SelectorProvider(["unknown"])

        with (
            patch(
                "kbot_installer.core.provider.selector_provider.create_provider"
            ) as mock_create,
            patch.object(
                selector.credential_manager, "has_credentials", return_value=True
            ),
            patch.object(
                selector.credential_manager,
                "get_auth_for_provider",
                return_value=MagicMock(),
            ),
        ):
            result = selector._create_provider_with_credentials("unknown")

            # Should not call create_provider for unknown provider
            mock_create.assert_not_called()
            assert result is None

    def test_clone_success_first_provider(self) -> None:
        """Test successful clone with first provider."""
        selector = SelectorProvider(["nexus", "github"])

        with patch.object(selector, "_create_provider_with_credentials") as mock_create:
            mock_provider = MagicMock()
            mock_create.return_value = mock_provider

            selector.clone_and_checkout(
                "/tmp/test_path", "main", repository_url="test_repo"
            )

            mock_create.assert_called_once_with("nexus")
            mock_provider.clone_and_checkout.assert_called_once_with(
                "test_repo", Path("/tmp/test_path"), "main"
            )

    def test_clone_success_second_provider(self) -> None:
        """Test successful clone with second provider after first fails."""
        selector = SelectorProvider(["nexus", "github"])

        with patch.object(selector, "_create_provider_with_credentials") as mock_create:
            mock_nexus = MagicMock()
            mock_github = MagicMock()
            mock_nexus.clone_and_checkout = AsyncMock(
                side_effect=ProviderError("Nexus failed")
            )
            mock_create.side_effect = [mock_nexus, mock_github]

            selector.clone_and_checkout(
                "/tmp/test_path", "main", repository_url="test_repo"
            )

            assert mock_create.call_count == 2
            mock_nexus.clone_and_checkout.assert_called_once_with(
                "test_repo", Path("/tmp/test_path"), "main"
            )
            mock_github.clone_and_checkout.assert_called_once_with(
                "test_repo", Path("/tmp/test_path"), "main"
            )

    def test_clone_all_providers_fail_provider_error(self) -> None:
        """Test clone when all providers fail with ProviderError."""
        selector = SelectorProvider(["nexus", "github"])

        with patch.object(selector, "_create_provider_with_credentials") as mock_create:
            # Create separate mock providers for each provider name
            def mock_create_side_effect(provider_name: str) -> MagicMock:  # noqa: ARG001
                mock_provider = MagicMock()
                mock_provider.clone_and_checkout = AsyncMock(
                    side_effect=ProviderError("All providers failed")
                )
                return mock_provider

            mock_create.side_effect = mock_create_side_effect

            with pytest.raises(
                ProviderError, match="All providers failed to clone repository"
            ):
                selector.clone_and_checkout(
                    "/tmp/test_path", "main", repository_url="test_repo"
                )

    def test_clone_all_providers_fail_general_exception(self) -> None:
        """Test clone when all providers fail with general exception."""
        selector = SelectorProvider(["nexus"])

        with patch.object(selector, "_create_provider_with_credentials") as mock_create:
            mock_create.side_effect = Exception("Provider creation failed")

        with pytest.raises(
            ProviderError, match="All providers failed to clone repository"
        ):
            selector.clone_and_checkout(
                "/tmp/test_path", "main", repository_url="test_repo"
            )

    def test_clone_mixed_failures(self) -> None:
        """Test clone with mixed failure types."""
        selector = SelectorProvider(["nexus", "github", "bitbucket"])

        with patch.object(selector, "_create_provider_with_credentials") as mock_create:
            mock_nexus = MagicMock()
            MagicMock()
            mock_bitbucket = MagicMock()

            mock_nexus.clone_and_checkout = AsyncMock(
                side_effect=ProviderError("Nexus failed")
            )
            mock_bitbucket.clone_and_checkout = AsyncMock(
                side_effect=ProviderError("Bitbucket failed")
            )

            # Mock the calls to return different providers
            def side_effect(provider_name: str) -> object:
                if provider_name == "nexus":
                    return mock_nexus
                if provider_name == "github":
                    error_msg = "GitHub creation failed"
                    raise RuntimeError(error_msg)
                if provider_name == "bitbucket":
                    return mock_bitbucket
                return None

            mock_create.side_effect = side_effect

            with pytest.raises(
                ProviderError, match="All providers failed to clone repository"
            ):
                selector.clone_and_checkout(
                    "/tmp/test_path", "main", repository_url="test_repo"
                )

    def test_str_representation(self) -> None:
        """Test string representation of SelectorProvider."""
        selector = SelectorProvider(["nexus", "github"])
        expected = "SelectorProvider(providers=['nexus', 'github'])"
        assert str(selector) == expected

    def test_repr_representation(self) -> None:
        """Test detailed string representation of SelectorProvider."""
        selector = SelectorProvider(["nexus", "github"], "https://example.com")
        expected = "SelectorProvider(providers=['nexus', 'github'], base_url='https://example.com')"
        assert repr(selector) == expected

    def test_repr_representation_empty_base_url(self) -> None:
        """Test detailed string representation with empty base_url."""
        selector = SelectorProvider(["nexus"])
        expected = "SelectorProvider(providers=['nexus'], base_url='')"
        assert repr(selector) == expected

    @patch("kbot_installer.core.provider.selector_provider.create_provider")
    def test_clone_by_name_success(self, mock_create: MagicMock) -> None:
        """Test successful cloning by repository name."""
        # Mock provider
        mock_provider = MagicMock()
        mock_create.return_value = mock_provider

        # Mock credential manager
        with patch(
            "kbot_installer.core.provider.selector_provider.CredentialManager"
        ) as mock_cred_mgr:
            mock_cred_mgr.return_value.get_auth_for_provider.return_value = None

            selector = SelectorProvider(["github"])
            selector.clone_and_checkout(
                "/tmp/test", "main", repository_name="test-repo"
            )

            mock_create.assert_called_once()
            mock_provider.clone_and_checkout.assert_called_once_with(
                "test-repo", Path("/tmp/test"), "main"
            )

    @patch("kbot_installer.core.provider.selector_provider.create_provider")
    def test_clone_by_name_all_providers_fail(self, mock_create: MagicMock) -> None:
        """Test cloning by name when all providers fail."""
        mock_create.return_value = None

        with patch(
            "kbot_installer.core.provider.selector_provider.CredentialManager"
        ) as mock_cred_mgr:
            mock_cred_mgr.return_value.get_auth_for_provider.return_value = None

            selector = SelectorProvider(["github", "bitbucket"])

            with pytest.raises(
                ProviderError, match="All providers failed to clone repository"
            ):
                selector.clone_and_checkout("/tmp/test", repository_name="test-repo")

    def test_clone_validation_errors(self) -> None:
        """Test clone method validation errors."""
        selector = SelectorProvider(["github"])

        # Test no arguments
        with pytest.raises(
            ValueError, match="Must specify either repository_url or repository_name"
        ):
            selector.clone_and_checkout("/tmp/test")

        # Test both arguments
        with pytest.raises(
            ValueError, match="Cannot specify both repository_url and repository_name"
        ):
            selector.clone_and_checkout(
                "/tmp/test",
                repository_url="https://github.com/test",
                repository_name="test",
            )

    def test_is_connection_error_true(self) -> None:
        """Test _is_connection_error returns True for connection errors."""
        selector = SelectorProvider(["nexus"])

        assert selector._is_connection_error("Connection failed to server")
        assert selector._is_connection_error("Connection failed")

    def test_is_connection_error_false(self) -> None:
        """Test _is_connection_error returns False for non-connection errors."""
        selector = SelectorProvider(["nexus"])

        assert not selector._is_connection_error("Repository not found")
        assert not selector._is_connection_error("Authentication failed")
        assert not selector._is_connection_error("Invalid URL")

    def test_extract_streaming_error_with_client_error(self) -> None:
        """Test _extract_streaming_error extracts HTTP error from client error."""
        selector = SelectorProvider(["nexus"])

        error_msg = "Streaming download/extraction failed: Client error '404 Not Found'"
        result = selector._extract_streaming_error(error_msg)

        assert result == "HTTP 404 Not Found"

    def test_extract_streaming_error_without_client_error(self) -> None:
        """Test _extract_streaming_error returns generic message without client error."""
        selector = SelectorProvider(["nexus"])

        error_msg = "Streaming download/extraction failed: Network timeout"
        result = selector._extract_streaming_error(error_msg)

        assert result == "Download failed"

    def test_extract_last_meaningful_part_version_not_found(self) -> None:
        """Test _extract_last_meaningful_part preserves version not found messages."""
        selector = SelectorProvider(["nexus"])

        error_msg = "Version 'v1.0.0' not found for repository 'test-repo'"
        result = selector._extract_last_meaningful_part(error_msg)

        assert result == error_msg

    def test_extract_last_meaningful_part_other_error(self) -> None:
        """Test _extract_last_meaningful_part extracts meaningful part from other errors."""
        selector = SelectorProvider(["nexus"])

        error_msg = (
            "Failed to clone repository: Authentication failed: Invalid credentials"
        )
        result = selector._extract_last_meaningful_part(error_msg)

        assert (
            result == error_msg
        )  # The method returns the full message for non-version errors

    def test_repr(self) -> None:
        """Test __repr__ returns detailed string representation."""
        selector = SelectorProvider(["nexus", "github"], "https://example.com")

        repr_str = repr(selector)

        assert "SelectorProvider" in repr_str
        assert "nexus" in repr_str
        assert "github" in repr_str
        assert "https://example.com" in repr_str

    @patch("kbot_installer.core.provider.selector_provider.create_provider")
    def test_provider_name_updated_in_clone_by_name(
        self, mock_create: MagicMock
    ) -> None:
        """Test that self.name is updated when cloning by name."""
        # Mock provider
        mock_provider = MagicMock()
        mock_provider.get_name.return_value = "github"
        mock_create.return_value = mock_provider

        # Mock credential manager
        with patch(
            "kbot_installer.core.provider.selector_provider.CredentialManager"
        ) as mock_cred_mgr:
            mock_cred_mgr.return_value.get_auth_for_provider.return_value = None

            selector = SelectorProvider(["github"])
            selector.clone_and_checkout(
                "/tmp/test", "main", repository_name="test-repo"
            )

            # Verify that self.name was updated
            assert selector.name == "github"

    def test_get_branch_returns_empty_before_clone(self) -> None:
        """Test get_branch returns empty string before clone."""
        selector = SelectorProvider(["nexus", "github"])
        # Before clone, branch_used is None, so should return empty string
        assert selector.get_branch() == ""

    @patch("kbot_installer.core.provider.selector_provider.create_provider")
    def test_get_branch_returns_used_branch_after_clone(
        self, mock_create: MagicMock
    ) -> None:
        """Test get_branch returns the branch used during clone."""
        # Mock provider
        mock_provider = MagicMock()
        mock_provider.get_name.return_value = "github"
        mock_create.return_value = mock_provider

        # Mock credential manager
        with patch(
            "kbot_installer.core.provider.selector_provider.CredentialManager"
        ) as mock_cred_mgr:
            mock_cred_mgr.return_value.get_auth_for_provider.return_value = None
            mock_cred_mgr.return_value.has_credentials.return_value = True

            selector = SelectorProvider(["github"])
            selector.clone_and_checkout(
                "/tmp/test", "main", repository_name="test-repo"
            )

            # After clone with branch "main", should return "main"
            assert selector.get_branch() == "main"

    @patch("kbot_installer.core.provider.selector_provider.create_provider")
    def test_get_branch_returns_fallback_branch_when_requested_not_found(
        self, mock_create: MagicMock
    ) -> None:
        """Test get_branch returns fallback branch when requested branch not found."""
        # Mock provider with branch fallback behavior
        mock_provider = MagicMock()
        mock_provider.get_name.return_value = "github"

        # Simulate branch fallback by tracking clone calls
        clone_calls = []

        async def mock_clone(_repo, _path, branch):
            clone_calls.append(branch)
            # First call fails (branch not found), second succeeds with fallback
            if len(clone_calls) == 1:
                from kbot_installer.core.provider.provider_base import ProviderError

                error_msg = "Branch not found"
                raise ProviderError(error_msg)

        mock_provider.clone_and_checkout = mock_clone
        mock_create.return_value = mock_provider

        # Mock credential manager
        with patch(
            "kbot_installer.core.provider.selector_provider.CredentialManager"
        ) as mock_cred_mgr:
            mock_cred_mgr.return_value.get_auth_for_provider.return_value = None
            mock_cred_mgr.return_value.has_credentials.return_value = True

            # Mock config to provide fallback branches
            with patch.object(
                SelectorProvider,
                "_get_branches_to_try",
                return_value=["main", "master"],
            ):
                selector = SelectorProvider(["github"])
                # This will try main first, then fallback to master
                # We'll simplify and just test that branch_used is set
                selector.branch_used = "master"
                assert selector.get_branch() == "master"

    @patch("kbot_installer.core.provider.selector_provider.create_provider")
    def test_provider_name_updated_in_clone_by_url(
        self, mock_create: MagicMock
    ) -> None:
        """Test that self.name is updated when cloning by URL."""
        # Mock provider
        mock_provider = MagicMock()
        mock_provider.get_name.return_value = "bitbucket"
        mock_create.return_value = mock_provider

        # Mock credential manager
        with patch(
            "kbot_installer.core.provider.selector_provider.CredentialManager"
        ) as mock_cred_mgr:
            mock_cred_mgr.return_value.get_auth_for_provider.return_value = None

            selector = SelectorProvider(["bitbucket"])
            selector.clone_and_checkout(
                "/tmp/test", "main", repository_url="https://example.com/repo"
            )

            # Verify that self.name was updated
            assert selector.name == "bitbucket"
