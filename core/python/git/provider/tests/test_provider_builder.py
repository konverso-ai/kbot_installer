"""Tests for the provider_builder module."""

from unittest.mock import ANY, MagicMock, patch

import pytest

from git.provider.credential_manager import CredentialManager
from git.provider.errors import ProviderError
from git.provider.provider_builder import build_provider


class TestBuildProvider:
    """Test cases for build_provider."""

    def _config_with(self, **provider_config: MagicMock) -> MagicMock:
        """Build a minimal config mock exposing ``get_provider_config``."""
        config = MagicMock()
        config.get_provider_config.side_effect = provider_config.get
        return config

    def test_returns_none_when_provider_not_configured(self) -> None:
        """Test that an unconfigured provider name returns None."""
        config = self._config_with()
        credential_manager = MagicMock(spec=CredentialManager)

        result = build_provider("unknown", config, credential_manager)

        assert result is None

    def test_returns_none_when_credentials_missing(self) -> None:
        """Test that a provider requiring credentials returns None without them."""
        provider_config = MagicMock(kwargs={})
        config = self._config_with(storage=provider_config)
        credential_manager = MagicMock(spec=CredentialManager)
        credential_manager.has_credentials.return_value = False

        result = build_provider("storage", config, credential_manager)

        assert result is None

    def test_github_and_bitbucket_allow_anonymous_access(self) -> None:
        """Test that github/bitbucket can be built even without credentials."""
        provider_config = MagicMock(kwargs={"account_name": "konverso-ai"})
        config = self._config_with(github=provider_config)
        credential_manager = MagicMock(spec=CredentialManager)
        credential_manager.has_credentials.return_value = False
        credential_manager.get_auth_for_provider.return_value = None

        with patch("git.provider.provider_builder.add_provider") as mock_create:
            mock_create.return_value = MagicMock()
            result = build_provider("github", config, credential_manager)

        mock_create.assert_called_once_with(name="github", account_name="konverso-ai")
        assert result is mock_create.return_value

    def test_storage_provider_receives_config_and_quiet(self) -> None:
        """Test that the storage provider is given config/quiet kwargs."""
        provider_config = MagicMock(kwargs={})
        config = self._config_with(storage=provider_config)
        credential_manager = MagicMock(spec=CredentialManager)
        credential_manager.has_credentials.return_value = True
        credential_manager.get_auth_for_provider.return_value = None

        with patch("git.provider.provider_builder.add_provider") as mock_create:
            mock_create.return_value = MagicMock()
            build_provider("storage", config, credential_manager, quiet=True)

        mock_create.assert_called_once_with(name="storage", config=config, quiet=True)

    def test_auth_added_when_available(self) -> None:
        """Test that resolved auth is forwarded to the provider constructor."""
        provider_config = MagicMock(kwargs={"account_name": "acme"})
        config = self._config_with(github=provider_config)
        credential_manager = MagicMock(spec=CredentialManager)
        credential_manager.has_credentials.return_value = True
        mock_auth = MagicMock()
        credential_manager.get_auth_for_provider.return_value = mock_auth

        with patch("git.provider.provider_builder.add_provider") as mock_create:
            mock_create.return_value = MagicMock()
            build_provider("github", config, credential_manager)

        mock_create.assert_called_once_with(
            name="github", account_name="acme", auth=ANY
        )

    def test_returns_none_when_creation_raises_provider_error(self) -> None:
        """Test that a ProviderError during creation is swallowed as None."""
        provider_config = MagicMock(kwargs={})
        config = self._config_with(github=provider_config)
        credential_manager = MagicMock(spec=CredentialManager)
        credential_manager.has_credentials.return_value = True
        credential_manager.get_auth_for_provider.return_value = None

        with patch("git.provider.provider_builder.add_provider") as mock_create:
            mock_create.side_effect = ProviderError("boom")
            result = build_provider("github", config, credential_manager)

        assert result is None

    def test_returns_none_when_creation_raises_generic_exception(self) -> None:
        """Test that an unexpected exception during creation is swallowed as None."""
        provider_config = MagicMock(kwargs={})
        config = self._config_with(github=provider_config)
        credential_manager = MagicMock(spec=CredentialManager)
        credential_manager.has_credentials.return_value = True
        credential_manager.get_auth_for_provider.return_value = None

        with patch("git.provider.provider_builder.add_provider") as mock_create:
            mock_create.side_effect = RuntimeError("boom")
            result = build_provider("github", config, credential_manager)

        assert result is None

    def test_raises_provider_error_on_invalid_configuration(self) -> None:
        """Test that a ValueError during creation is wrapped in ProviderError."""
        provider_config = MagicMock(kwargs={})
        config = self._config_with(github=provider_config)
        credential_manager = MagicMock(spec=CredentialManager)
        credential_manager.has_credentials.return_value = True
        credential_manager.get_auth_for_provider.return_value = None

        with (
            patch("git.provider.provider_builder.add_provider") as mock_create,
            pytest.raises(ProviderError, match="Failed to configure provider"),
        ):
            mock_create.side_effect = ValueError("bad config")
            build_provider("github", config, credential_manager)
