"""Tests for SelectorProvider detailed error reporting."""

from unittest.mock import MagicMock, patch

import pytest

from kbot_installer.core.provider.provider_base import ProviderError
from kbot_installer.core.provider.selector_provider import SelectorProvider


class TestSelectorProviderErrorDetails:
    """Test cases for detailed error reporting in SelectorProvider."""

    def test_clone_by_name_all_providers_fail_detailed_error(self) -> None:
        """Test that all provider failures are reported in detail."""
        # Create SelectorProvider with test providers
        provider = SelectorProvider(
            providers=["nexus", "github", "bitbucket"],
            config={"nexus": {}, "github": {}, "bitbucket": {}},
        )

        # Mock the credential manager to return credentials for all providers
        with patch.object(provider, "credential_manager") as mock_cred_manager:
            mock_cred_manager.get_missing_credentials_info.return_value = []

            # Mock _create_provider_with_credentials to return mock providers
            with patch.object(
                provider, "_create_provider_with_credentials"
            ) as mock_create:
                # Create mock providers that all fail with different errors
                mock_nexus = MagicMock()
                mock_nexus.clone_and_checkout = MagicMock(
                    side_effect=ProviderError(
                        "Version 'release-2021.03-dev' not found for repository 'test-repo'. Available versions: dev, master, release-2025.03"
                    )
                )
                mock_nexus.get_name.return_value = "nexus"

                mock_github = MagicMock()
                mock_github.clone_and_checkout = MagicMock(
                    side_effect=ProviderError("Repository 'test-repo' not found")
                )
                mock_github.get_name.return_value = "github"

                mock_bitbucket = MagicMock()
                mock_bitbucket.clone_and_checkout = MagicMock(
                    side_effect=ProviderError("Authentication failed")
                )
                mock_bitbucket.get_name.return_value = "bitbucket"

                # Configure mock to return different providers
                def create_provider_side_effect(provider_name):
                    providers = {
                        "nexus": mock_nexus,
                        "github": mock_github,
                        "bitbucket": mock_bitbucket,
                    }
                    return providers.get(provider_name)

                mock_create.side_effect = create_provider_side_effect

                # Test that all provider errors are included in the final error
                with pytest.raises(ProviderError) as exc_info:
                    provider._clone_by_name(
                        "test-repo", "/tmp/test", "release-2021.03-dev"
                    )

                error_msg = str(exc_info.value)

                # Check that all provider errors are included
                assert (
                    "All providers failed to clone repository 'test-repo'" in error_msg
                )
                assert "nexus:" in error_msg
                assert "github:" in error_msg
                assert "bitbucket:" in error_msg
                assert "Version 'release-2021.03-dev' not found" in error_msg
                assert "Repository 'test-repo' not found" in error_msg
                assert "Authentication failed" in error_msg

    def test_clone_by_name_some_providers_skipped_detailed_error(self) -> None:
        """Test that skipped providers are also reported in detail."""
        # Create SelectorProvider with test providers
        provider = SelectorProvider(
            providers=["nexus", "github", "bitbucket"],
            config={"nexus": {}, "github": {}, "bitbucket": {}},
        )

        # Mock the credential manager to return missing credentials for some providers
        with patch.object(provider, "credential_manager") as mock_cred_manager:

            def missing_creds_side_effect(provider_name):
                creds_map = {
                    "nexus": ["username", "password"],
                    "github": ["token"],
                }
                return creds_map.get(provider_name, [])

            mock_cred_manager.get_missing_credentials_info.side_effect = (
                missing_creds_side_effect
            )

            # Mock _create_provider_with_credentials to return None for some providers
            with patch.object(
                provider, "_create_provider_with_credentials"
            ) as mock_create:

                def create_provider_side_effect(provider_name):
                    if provider_name == "bitbucket":
                        # Only bitbucket has credentials
                        mock_bitbucket = MagicMock()
                        mock_bitbucket.clone_and_checkout = MagicMock(
                            side_effect=ProviderError(
                                "Repository 'test-repo' not found"
                            )
                        )
                        mock_bitbucket.get_name.return_value = "bitbucket"
                        return mock_bitbucket
                    # nexus and github have no credentials
                    return None

                mock_create.side_effect = create_provider_side_effect

                # Test that all provider errors (including skipped ones) are included
                with pytest.raises(ProviderError) as exc_info:
                    provider._clone_by_name(
                        "test-repo", "/tmp/test", "release-2021.03-dev"
                    )

                error_msg = str(exc_info.value)

                # Check that all provider errors are included
                assert (
                    "All providers failed to clone repository 'test-repo'" in error_msg
                )
                assert "nexus:" in error_msg
                assert "github:" in error_msg
                assert "bitbucket:" in error_msg
                assert "Missing credentials:" in error_msg
                assert "Repository 'test-repo' not found" in error_msg

    def test_clone_by_url_all_providers_fail_detailed_error(self) -> None:
        """Test that all provider failures are reported in detail for URL cloning."""
        # Create SelectorProvider with test providers
        provider = SelectorProvider(
            providers=["nexus", "github", "bitbucket"],
            config={"nexus": {}, "github": {}, "bitbucket": {}},
        )

        # Mock the credential manager to return credentials for all providers
        with patch.object(provider, "credential_manager") as mock_cred_manager:
            mock_cred_manager.get_missing_credentials_info.return_value = []

            # Mock _create_provider_with_credentials to return mock providers
            with patch.object(
                provider, "_create_provider_with_credentials"
            ) as mock_create:
                # Create mock providers that all fail with different errors
                mock_nexus = MagicMock()
                mock_nexus.clone_and_checkout = MagicMock(
                    side_effect=ProviderError(
                        "Version 'release-2021.03-dev' not found for repository 'test-repo'. Available versions: dev, master, release-2025.03"
                    )
                )
                mock_nexus.get_name.return_value = "nexus"

                mock_github = MagicMock()
                mock_github.clone_and_checkout = MagicMock(
                    side_effect=ProviderError("Repository 'test-repo' not found")
                )
                mock_github.get_name.return_value = "github"

                mock_bitbucket = MagicMock()
                mock_bitbucket.clone_and_checkout = MagicMock(
                    side_effect=ProviderError("Authentication failed")
                )
                mock_bitbucket.get_name.return_value = "bitbucket"

                # Configure mock to return different providers
                def create_provider_side_effect(provider_name):
                    providers = {
                        "nexus": mock_nexus,
                        "github": mock_github,
                        "bitbucket": mock_bitbucket,
                    }
                    return providers.get(provider_name)

                mock_create.side_effect = create_provider_side_effect

                # Test that all provider errors are included in the final error
                with pytest.raises(ProviderError) as exc_info:
                    provider._clone_by_url(
                        "test-repo", "/tmp/test", "release-2021.03-dev"
                    )

                error_msg = str(exc_info.value)

                # Check that all provider errors are included
                assert (
                    "All providers failed to clone repository 'test-repo'" in error_msg
                )
                assert "nexus:" in error_msg
                assert "github:" in error_msg
                assert "bitbucket:" in error_msg
                assert "Version 'release-2021.03-dev' not found" in error_msg
                assert "Repository 'test-repo' not found" in error_msg
                assert "Authentication failed" in error_msg

    def test_clone_by_name_success_returns_early(self) -> None:
        """Test that successful clone returns early without error details."""
        # Create SelectorProvider with test providers
        provider = SelectorProvider(
            providers=["nexus", "github", "bitbucket"],
            config={"nexus": {}, "github": {}, "bitbucket": {}},
        )

        # Mock the credential manager to return credentials for all providers
        with patch.object(provider, "credential_manager") as mock_cred_manager:
            mock_cred_manager.get_missing_credentials_info.return_value = []

            # Mock _create_provider_with_credentials to return a successful provider
            with patch.object(
                provider, "_create_provider_with_credentials"
            ) as mock_create:
                # Create a mock provider that succeeds
                mock_nexus = MagicMock()
                mock_nexus.clone_and_checkout = MagicMock(return_value=None)  # Success
                mock_nexus.get_name.return_value = "nexus"

                # Only return nexus provider, others should not be called
                def create_provider_side_effect(provider_name):
                    if provider_name == "nexus":
                        return mock_nexus
                    return None

                mock_create.side_effect = create_provider_side_effect

                # Test that it succeeds without raising an exception
                provider._clone_by_name("test-repo", "/tmp/test", "release-2021.03-dev")

                # Verify that only nexus was called
                mock_create.assert_called_once_with("nexus")
