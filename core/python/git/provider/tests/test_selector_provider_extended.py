"""Extended tests for SelectorProvider."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from git.provider.config import (
    AzureStorageSettings,
    NexusStorageSettings,
    OciStorageSettings,
    ProvidersConfig,
    S3StorageSettings,
    StorageSectionConfig,
)
from git.provider.selector_provider import SelectorProvider


def _empty_providers_config() -> ProvidersConfig:
    """Build a minimal valid providers config for tests."""
    return ProvidersConfig(
        provider={},
        storage=StorageSectionConfig(
            backend="nexus",
            nexus=NexusStorageSettings(domain="example.com", repository="raw"),
            s3=S3StorageSettings(bucket_name="bucket"),
            azure=AzureStorageSettings(
                account_url="https://example.blob.core.windows.net",
                container_name="container",
            ),
            oci=OciStorageSettings(bucket_name="bucket", namespace_name="ns"),
        ),
    )


class TestSelectorProviderExtended:
    """Extended test cases for SelectorProvider."""

    def test_init_with_custom_config(self) -> None:
        """Test SelectorProvider initialization with custom config."""
        custom_config = _empty_providers_config()
        providers = ["storage", "github"]

        selector = SelectorProvider(
            providers=providers, base_url="https://custom.com", config=custom_config
        )

        assert selector.providers == providers
        assert selector.base_url == "https://custom.com"
        assert selector.config == custom_config
        assert selector.credential_manager is not None

    def test_init_with_empty_providers(self) -> None:
        """Test SelectorProvider initialization with empty providers list."""
        selector = SelectorProvider(providers=[])

        assert selector.providers == []
        assert selector.base_url == ""
        assert selector.credential_manager is not None

    def test_create_provider_with_credentials_success(self) -> None:
        """Test successful provider creation with credentials."""
        selector = SelectorProvider(providers=["storage"])

        with (
            patch.object(
                selector.credential_manager, "has_credentials", return_value=True
            ),
            patch.object(ProvidersConfig, "get_provider_config") as mock_get_config,
            patch.object(
                selector.credential_manager,
                "get_auth_for_provider",
                return_value=MagicMock(),
            ),
            patch(
                "git.provider.provider_builder.add_provider"
            ) as mock_create,
        ):
            # Setup mocks
            mock_config = MagicMock()
            mock_config.kwargs = {"domain": "example.com", "repository": "test"}
            mock_get_config.return_value = mock_config
            mock_create.return_value = MagicMock()

            # Test
            result = selector._create_provider_with_credentials("storage")

            # Verify
            assert result is not None
            mock_create.assert_called_once()

    def test_create_provider_with_credentials_no_credentials(self) -> None:
        """Test provider creation when no credentials are available."""
        selector = SelectorProvider(providers=["storage"])

        with patch.object(
            selector.credential_manager, "has_credentials", return_value=False
        ):
            result = selector._create_provider_with_credentials("storage")
            assert result is None

    def test_create_provider_with_credentials_no_config(self) -> None:
        """Test provider creation when no config is available."""
        selector = SelectorProvider(providers=["storage"])

        with (
            patch.object(
                selector.credential_manager, "has_credentials", return_value=True
            ),
            patch.object(ProvidersConfig, "get_provider_config", return_value=None),
        ):
            result = selector._create_provider_with_credentials("storage")
            assert result is None

    def test_create_provider_with_credentials_creation_fails(self) -> None:
        """Test provider creation when provider creation fails."""
        selector = SelectorProvider(providers=["storage"])

        with (
            patch.object(
                selector.credential_manager, "has_credentials", return_value=True
            ),
            patch.object(ProvidersConfig, "get_provider_config") as mock_get_config,
            patch.object(
                selector.credential_manager,
                "get_auth_for_provider",
                return_value=MagicMock(),
            ),
            patch(
                "git.provider.provider_builder.add_provider"
            ) as mock_create,
        ):
            # Setup mocks
            mock_config = MagicMock()
            mock_config.kwargs = {"domain": "example.com", "repository": "test"}
            mock_get_config.return_value = mock_config
            mock_create.side_effect = Exception("Creation failed")

            # Test
            result = selector._create_provider_with_credentials("storage")
            assert result is None

    def test_clone_both_url_and_name_provided(self) -> None:
        """Test clone with both repository_url and repository_name provided."""
        selector = SelectorProvider(providers=["storage"])

        with pytest.raises(
            ValueError, match="Cannot specify both repository_url and repository_name"
        ):
            selector.clone_and_checkout(
                target_path="/tmp/test",
                repository_url="https://example.com/repo",
                repository_name="test-repo",
            )

    def test_clone_neither_url_nor_name_provided(self) -> None:
        """Test clone with neither repository_url nor repository_name provided."""
        selector = SelectorProvider(providers=["storage"])

        with pytest.raises(
            ValueError, match="Must specify either repository_url or repository_name"
        ):
            selector.clone_and_checkout(target_path="/tmp/test")

    def test_clone_by_url_success(self) -> None:
        """Test successful clone by URL."""
        selector = SelectorProvider(providers=["storage"])

        with patch.object(selector, "_clone_by_url") as mock_clone_by_url:
            selector.clone_and_checkout(
                target_path="/tmp/test", repository_url="https://example.com/repo"
            )
            mock_clone_by_url.assert_called_once_with(
                "https://example.com/repo", "/tmp/test", None, commit=None
            )

    def test_clone_by_name_success(self) -> None:
        """Test successful clone by name."""
        selector = SelectorProvider(providers=["storage"])

        with patch.object(selector, "_clone_by_name") as mock_clone_by_name:
            selector.clone_and_checkout(
                target_path="/tmp/test", repository_name="test-repo"
            )
            mock_clone_by_name.assert_called_once_with(
                "test-repo", "/tmp/test", None, commit=None
            )

    def test_clone_with_branch(self) -> None:
        """Test clone with specific branch."""
        selector = SelectorProvider(providers=["storage"])

        with patch.object(selector, "_clone_by_name") as mock_clone_by_name:
            selector.clone_and_checkout(
                target_path="/tmp/test", repository_name="test-repo", branch="dev"
            )
            mock_clone_by_name.assert_called_once_with(
                "test-repo", "/tmp/test", "dev", commit=None
            )

    def test_clone_by_url_with_string_path(self) -> None:
        """Test clone by URL with string path."""
        selector = SelectorProvider(providers=["storage"])

        with patch.object(selector, "_clone_by_url") as mock_clone_by_url:
            selector.clone_and_checkout(
                target_path="/tmp/test", repository_url="https://example.com/repo"
            )
            mock_clone_by_url.assert_called_once_with(
                "https://example.com/repo", "/tmp/test", None, commit=None
            )

    def test_clone_by_name_with_path_object(self) -> None:
        """Test clone by name with Path object."""
        selector = SelectorProvider(providers=["storage"])

        with patch.object(selector, "_clone_by_name") as mock_clone_by_name:
            target_path = Path("/tmp/test")
            selector.clone_and_checkout(
                target_path=target_path, repository_name="test-repo"
            )
            mock_clone_by_name.assert_called_once_with(
                "test-repo", target_path, None, commit=None
            )

    def test_credential_manager_initialization(self) -> None:
        """Test that credential manager is properly initialized."""
        selector = SelectorProvider(providers=["storage"])

        assert selector.credential_manager is not None
        assert hasattr(selector.credential_manager, "has_credentials")
        assert hasattr(selector.credential_manager, "get_auth_for_provider")

    def test_config_initialization(self) -> None:
        """Test that config is properly initialized."""
        selector = SelectorProvider(providers=["storage"])

        assert selector.config is not None
        assert hasattr(selector.config, "get_provider_config")

    def test_providers_attribute(self) -> None:
        """Test that providers attribute is properly set."""
        providers = ["storage", "github", "bitbucket"]
        selector = SelectorProvider(providers=providers)

        assert selector.providers == providers

    def test_base_url_attribute(self) -> None:
        """Test that base_url attribute is properly set."""
        base_url = "https://custom.example.com"
        selector = SelectorProvider(providers=["storage"], base_url=base_url)

        assert selector.base_url == base_url

    def test_base_url_default(self) -> None:
        """Test that base_url defaults to empty string."""
        selector = SelectorProvider(providers=["storage"])

        assert selector.base_url == ""

    def test_create_provider_with_credentials_auth_none(self) -> None:
        """Test provider creation when auth is None."""
        selector = SelectorProvider(providers=["storage"])

        with (
            patch.object(
                selector.credential_manager, "has_credentials", return_value=True
            ),
            patch.object(ProvidersConfig, "get_provider_config") as mock_get_config,
            patch.object(
                selector.credential_manager, "get_auth_for_provider", return_value=None
            ),
            patch(
                "git.provider.provider_builder.add_provider"
            ) as mock_create,
        ):
            # Setup mocks
            mock_config = MagicMock()
            mock_config.kwargs = {"domain": "example.com", "repository": "test"}
            mock_get_config.return_value = mock_config
            mock_create.return_value = MagicMock()

            # Test
            result = selector._create_provider_with_credentials("storage")

            # Verify
            assert result is not None
            # Should not include auth in params since it's None
            call_args = mock_create.call_args
            assert "auth" not in call_args[1] or call_args[1]["auth"] is None
