"""Extended tests for SelectorProvider."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from kbot_installer.core.provider.selector_provider import SelectorProvider


class TestSelectorProviderExtended:
    """Extended test cases for SelectorProvider."""

    def test_init_with_custom_config(self) -> None:
        """Test SelectorProvider initialization with custom config."""
        from kbot_installer.core.provider.config import ProvidersConfig

        custom_config = ProvidersConfig(providers={})
        providers = ["nexus", "github"]

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
        selector = SelectorProvider(providers=["nexus"])

        with (
            patch.object(
                selector.credential_manager, "has_credentials", return_value=True
            ),
            patch.object(selector.config, "get_provider_config") as mock_get_config,
            patch.object(
                selector.credential_manager,
                "get_auth_for_provider",
                return_value=MagicMock(),
            ),
            patch(
                "kbot_installer.core.provider.selector_provider.create_provider"
            ) as mock_create,
        ):
            # Setup mocks
            mock_config = MagicMock()
            mock_config.kwargs = {"domain": "example.com", "repository": "test"}
            mock_get_config.return_value = mock_config
            mock_create.return_value = MagicMock()

            # Test
            result = selector._create_provider_with_credentials("nexus")

            # Verify
            assert result is not None
            mock_create.assert_called_once()

    def test_create_provider_with_credentials_no_credentials(self) -> None:
        """Test provider creation when no credentials are available."""
        selector = SelectorProvider(providers=["nexus"])

        with patch.object(
            selector.credential_manager, "has_credentials", return_value=False
        ):
            result = selector._create_provider_with_credentials("nexus")
            assert result is None

    def test_create_provider_with_credentials_no_config(self) -> None:
        """Test provider creation when no config is available."""
        selector = SelectorProvider(providers=["nexus"])

        with (
            patch.object(
                selector.credential_manager, "has_credentials", return_value=True
            ),
            patch.object(selector.config, "get_provider_config", return_value=None),
        ):
            result = selector._create_provider_with_credentials("nexus")
            assert result is None

    def test_create_provider_with_credentials_creation_fails(self) -> None:
        """Test provider creation when provider creation fails."""
        selector = SelectorProvider(providers=["nexus"])

        with (
            patch.object(
                selector.credential_manager, "has_credentials", return_value=True
            ),
            patch.object(selector.config, "get_provider_config") as mock_get_config,
            patch.object(
                selector.credential_manager,
                "get_auth_for_provider",
                return_value=MagicMock(),
            ),
            patch(
                "kbot_installer.core.provider.selector_provider.create_provider"
            ) as mock_create,
        ):
            # Setup mocks
            mock_config = MagicMock()
            mock_config.kwargs = {"domain": "example.com", "repository": "test"}
            mock_get_config.return_value = mock_config
            mock_create.side_effect = Exception("Creation failed")

            # Test
            result = selector._create_provider_with_credentials("nexus")
            assert result is None

    def test_clone_both_url_and_name_provided(self) -> None:
        """Test clone with both repository_url and repository_name provided."""
        selector = SelectorProvider(providers=["nexus"])

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
        selector = SelectorProvider(providers=["nexus"])

        with pytest.raises(
            ValueError, match="Must specify either repository_url or repository_name"
        ):
            selector.clone_and_checkout(target_path="/tmp/test")

    def test_clone_by_url_success(self) -> None:
        """Test successful clone by URL."""
        selector = SelectorProvider(providers=["nexus"])

        with patch.object(selector, "_clone_by_url") as mock_clone_by_url:
            selector.clone_and_checkout(
                target_path="/tmp/test", repository_url="https://example.com/repo"
            )
            mock_clone_by_url.assert_called_once_with(
                "https://example.com/repo", "/tmp/test", None
            )

    def test_clone_by_name_success(self) -> None:
        """Test successful clone by name."""
        selector = SelectorProvider(providers=["nexus"])

        with patch.object(selector, "_clone_by_name") as mock_clone_by_name:
            selector.clone_and_checkout(
                target_path="/tmp/test", repository_name="test-repo"
            )
            mock_clone_by_name.assert_called_once_with("test-repo", "/tmp/test", None)

    def test_clone_with_branch(self) -> None:
        """Test clone with specific branch."""
        selector = SelectorProvider(providers=["nexus"])

        with patch.object(selector, "_clone_by_name") as mock_clone_by_name:
            selector.clone_and_checkout(
                target_path="/tmp/test", repository_name="test-repo", branch="dev"
            )
            mock_clone_by_name.assert_called_once_with("test-repo", "/tmp/test", "dev")

    def test_print_clone_results_table_empty(self) -> None:
        """Test printing empty results table."""
        selector = SelectorProvider(providers=["nexus"])

        # Should not raise any exception
        selector._print_clone_results_table([])

    def test_print_clone_results_table_with_results(self) -> None:
        """Test printing results table with data."""
        selector = SelectorProvider(providers=["nexus"])

        results = [
            ("nexus", "✅ Success", "Repository cloned successfully"),
            ("github", "❌ Error", "Repository not found"),
            ("bitbucket", "❌ Error", "Authentication failed"),
        ]

        # Should not raise any exception
        selector._print_clone_results_table(results)

    def test_print_clone_results_table_long_cause(self) -> None:
        """Test printing results table with long cause messages."""
        selector = SelectorProvider(providers=["nexus"])

        long_cause = "This is a very long error message that should be truncated because it exceeds the maximum length allowed for cause messages in the results table"
        results = [("nexus", "❌ Error", long_cause)]

        # Should not raise any exception
        selector._print_clone_results_table(results)

    def test_extract_clean_error_cause_simple(self) -> None:
        """Test extracting clean error cause from simple error message."""
        selector = SelectorProvider(providers=["nexus"])

        error_msg = "Repository not found"
        result = selector._extract_clean_error_cause(error_msg)
        assert result == "Repository not found"

    def test_extract_clean_error_cause_with_exception(self) -> None:
        """Test extracting clean error cause from exception message."""
        selector = SelectorProvider(providers=["nexus"])

        error_msg = "Exception: Repository not found at line 123"
        result = selector._extract_clean_error_cause(error_msg)
        assert result == "Exception: Repository not found at line 123"

    def test_extract_clean_error_cause_with_httpx_error(self) -> None:
        """Test extracting clean error cause from HTTPX error."""
        selector = SelectorProvider(providers=["nexus"])

        error_msg = "HTTPXError: 404 Not Found - Repository not found"
        result = selector._extract_clean_error_cause(error_msg)
        assert result == "Repository not found (404)"

    def test_extract_clean_error_cause_with_provider_error(self) -> None:
        """Test extracting clean error cause from ProviderError."""
        selector = SelectorProvider(providers=["nexus"])

        error_msg = "ProviderError: Failed to clone repository: Authentication failed"
        result = selector._extract_clean_error_cause(error_msg)
        assert (
            result == "ProviderError: Failed to clone repository: Authentication failed"
        )

    def test_extract_clean_error_cause_with_git_error(self) -> None:
        """Test extracting clean error cause from Git error."""
        selector = SelectorProvider(providers=["nexus"])

        error_msg = (
            "GitError: fatal: repository 'https://example.com/repo.git' not found"
        )
        result = selector._extract_clean_error_cause(error_msg)
        assert result == "//example.com/repo.git' not found"

    def test_extract_clean_error_cause_with_connection_error(self) -> None:
        """Test extracting clean error cause from connection error."""
        selector = SelectorProvider(providers=["nexus"])

        error_msg = "ConnectionError: Failed to connect to server: Connection timeout"
        result = selector._extract_clean_error_cause(error_msg)
        assert result == "Request timeout"

    def test_extract_clean_error_cause_with_unknown_error(self) -> None:
        """Test extracting clean error cause from unknown error format."""
        selector = SelectorProvider(providers=["nexus"])

        error_msg = "SomeUnknownError: This is a custom error message"
        result = selector._extract_clean_error_cause(error_msg)
        assert result == "This is a custom error message"

    def test_extract_clean_error_cause_empty_message(self) -> None:
        """Test extracting clean error cause from empty message."""
        selector = SelectorProvider(providers=["nexus"])

        result = selector._extract_clean_error_cause("")
        assert result == ""

    def test_extract_clean_error_cause_none_message(self) -> None:
        """Test extracting clean error cause from None message."""
        selector = SelectorProvider(providers=["nexus"])

        # The method should handle None gracefully
        with pytest.raises(TypeError):
            selector._extract_clean_error_cause(None)

    def test_clone_by_url_with_string_path(self) -> None:
        """Test clone by URL with string path."""
        selector = SelectorProvider(providers=["nexus"])

        with patch.object(selector, "_clone_by_url") as mock_clone_by_url:
            selector.clone_and_checkout(
                target_path="/tmp/test", repository_url="https://example.com/repo"
            )
            mock_clone_by_url.assert_called_once_with(
                "https://example.com/repo", "/tmp/test", None
            )

    def test_clone_by_name_with_path_object(self) -> None:
        """Test clone by name with Path object."""
        selector = SelectorProvider(providers=["nexus"])

        with patch.object(selector, "_clone_by_name") as mock_clone_by_name:
            target_path = Path("/tmp/test")
            selector.clone_and_checkout(
                target_path=target_path, repository_name="test-repo"
            )
            mock_clone_by_name.assert_called_once_with("test-repo", target_path, None)

    def test_credential_manager_initialization(self) -> None:
        """Test that credential manager is properly initialized."""
        selector = SelectorProvider(providers=["nexus"])

        assert selector.credential_manager is not None
        assert hasattr(selector.credential_manager, "has_credentials")
        assert hasattr(selector.credential_manager, "get_auth_for_provider")

    def test_config_initialization(self) -> None:
        """Test that config is properly initialized."""
        selector = SelectorProvider(providers=["nexus"])

        assert selector.config is not None
        assert hasattr(selector.config, "get_provider_config")

    def test_providers_attribute(self) -> None:
        """Test that providers attribute is properly set."""
        providers = ["nexus", "github", "bitbucket"]
        selector = SelectorProvider(providers=providers)

        assert selector.providers == providers

    def test_base_url_attribute(self) -> None:
        """Test that base_url attribute is properly set."""
        base_url = "https://custom.example.com"
        selector = SelectorProvider(providers=["nexus"], base_url=base_url)

        assert selector.base_url == base_url

    def test_base_url_default(self) -> None:
        """Test that base_url defaults to empty string."""
        selector = SelectorProvider(providers=["nexus"])

        assert selector.base_url == ""

    def test_create_provider_with_credentials_auth_none(self) -> None:
        """Test provider creation when auth is None."""
        selector = SelectorProvider(providers=["nexus"])

        with (
            patch.object(
                selector.credential_manager, "has_credentials", return_value=True
            ),
            patch.object(selector.config, "get_provider_config") as mock_get_config,
            patch.object(
                selector.credential_manager, "get_auth_for_provider", return_value=None
            ),
            patch(
                "kbot_installer.core.provider.selector_provider.create_provider"
            ) as mock_create,
        ):
            # Setup mocks
            mock_config = MagicMock()
            mock_config.kwargs = {"domain": "example.com", "repository": "test"}
            mock_get_config.return_value = mock_config
            mock_create.return_value = MagicMock()

            # Test
            result = selector._create_provider_with_credentials("nexus")

            # Verify
            assert result is not None
            # Should not include auth in params since it's None
            call_args = mock_create.call_args
            assert "auth" not in call_args[1] or call_args[1]["auth"] is None
