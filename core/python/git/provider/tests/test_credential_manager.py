"""Tests for CredentialManager class."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

from auth.base import HttpAuthBase
from git.provider.config import ProvidersConfig
from git.provider.credential_manager import CredentialManager


class TestCredentialManager:
    """Test cases for CredentialManager class."""

    def test_initialization(self) -> None:
        """Test proper initialization of CredentialManager."""
        manager = CredentialManager()

        assert hasattr(manager, "config")
        assert manager.config is not None
        # Test that default configuration is loaded
        assert "storage" in manager.config.provider
        assert "github" in manager.config.provider
        assert "bitbucket" in manager.config.provider

        # Check specific environment variables
        assert manager.config.provider["storage"].env_vars == [
            "NEXUS_USERNAME",
            "NEXUS_PASSWORD",
        ]
        assert manager.config.provider["github"].env_vars == []
        assert manager.config.provider["bitbucket"].env_vars == []

    @patch.dict(
        os.environ, {"NEXUS_USERNAME": "test_user", "NEXUS_PASSWORD": "test_pass"}
    )
    def test_has_credentials_nexus_success(self) -> None:
        """Test has_credentials returns True when all Nexus credentials are available."""
        manager = CredentialManager()
        assert manager.has_credentials("storage") is True

    @patch.dict(os.environ, {"NEXUS_USER": "test_user", "NEXUS_PASSWORD": "test_pass"})
    def test_has_credentials_nexus_legacy_user_alias(self) -> None:
        """Test legacy NEXUS_USER alias is accepted for NEXUS_USERNAME."""
        manager = CredentialManager()
        assert manager.has_credentials("storage") is True

    @patch.dict(os.environ, {"NEXUS_USERNAME": "test_user"}, clear=True)
    def test_has_credentials_nexus_missing_password(self) -> None:
        """Test has_credentials returns False when Nexus password is missing."""
        manager = CredentialManager()
        assert manager.has_credentials("storage") is False

    @patch.dict(os.environ, {"NEXUS_PASSWORD": "test_pass"}, clear=True)
    def test_has_credentials_nexus_missing_username(self) -> None:
        """Test has_credentials returns False when Nexus username is missing."""
        manager = CredentialManager()
        assert manager.has_credentials("storage") is False

    @patch.dict(os.environ, {}, clear=True)
    def test_has_credentials_nexus_missing_all(self) -> None:
        """Test has_credentials returns False when all Nexus credentials are missing."""
        manager = CredentialManager()
        assert manager.has_credentials("storage") is False

    @patch.dict(os.environ, {"SSH_AUTH_SOCK": "/tmp/ssh-agent"}, clear=True)
    def test_has_credentials_github_success(self) -> None:
        """Test has_credentials returns True when SSH agent is available."""
        manager = CredentialManager()
        assert manager.has_credentials("github") is True

    @patch("credentials.ssh_credentials.Path.home")
    @patch.dict(os.environ, {}, clear=True)
    def test_has_credentials_github_missing(self, mock_home) -> None:
        """Test has_credentials returns False when SSH credentials are missing."""
        mock_home.return_value = Path("/empty/home")
        manager = CredentialManager()
        assert manager.has_credentials("github") is False

    @patch.dict(os.environ, {"SSH_AUTH_SOCK": "/tmp/ssh-agent"}, clear=True)
    def test_has_credentials_bitbucket_success(self) -> None:
        """Test has_credentials returns True when SSH agent is available."""
        manager = CredentialManager()
        assert manager.has_credentials("bitbucket") is True

    @patch("credentials.ssh_credentials.Path.home")
    @patch.dict(os.environ, {}, clear=True)
    def test_has_credentials_bitbucket_missing(self, mock_home) -> None:
        """Test has_credentials returns False when SSH credentials are missing."""
        mock_home.return_value = Path("/empty/home")
        manager = CredentialManager()
        assert manager.has_credentials("bitbucket") is False

    @patch.dict(os.environ, {}, clear=True)
    def test_has_credentials_unknown_provider(self) -> None:
        """Test has_credentials returns False for unknown provider."""
        manager = CredentialManager()
        assert manager.has_credentials("unknown") is False

    @patch.dict(
        os.environ, {"NEXUS_USERNAME": "test_user", "NEXUS_PASSWORD": "test_pass"}
    )
    @patch("git.provider.credential_manager.create_auth")
    def test_get_auth_for_provider_nexus_success(self, mock_create_auth) -> None:
        """Test get_auth_for_provider returns authentication object for Nexus when credentials are available."""
        manager = CredentialManager()
        mock_auth = MagicMock(spec=HttpAuthBase)
        mock_create_auth.return_value = mock_auth

        result = manager.get_auth_for_provider("storage")

        assert result is not None
        assert isinstance(result, HttpAuthBase)
        mock_create_auth.assert_called_once_with(
            "basic", username="test_user", password="test_pass"
        )

    @patch.dict(os.environ, {}, clear=True)
    def test_get_auth_for_provider_nexus_no_credentials(self) -> None:
        """Test get_auth_for_provider returns None for Nexus when credentials are not available."""
        manager = CredentialManager()

        result = manager.get_auth_for_provider("storage")

        assert result is None

    @patch.dict(
        os.environ, {"NEXUS_USERNAME": "test_user", "NEXUS_PASSWORD": "test_pass"}
    )
    @patch("git.provider.credential_manager.create_auth")
    def test_get_auth_for_provider_nexus_import_error(self, mock_create_auth) -> None:
        """Test get_auth_for_provider handles ImportError gracefully for Nexus."""
        manager = CredentialManager()
        mock_create_auth.side_effect = ImportError("Module not found")

        result = manager.get_auth_for_provider("storage")

        assert result is None

    @patch.dict(
        os.environ, {"NEXUS_USERNAME": "test_user", "NEXUS_PASSWORD": "test_pass"}
    )
    @patch("git.provider.credential_manager.create_auth")
    def test_get_auth_for_provider_nexus_general_exception(
        self, mock_create_auth
    ) -> None:
        """Test get_auth_for_provider handles general exceptions gracefully for Nexus."""
        manager = CredentialManager()
        mock_create_auth.side_effect = Exception("Unexpected error")

        result = manager.get_auth_for_provider("storage")

        assert result is None

    @patch("credentials.ssh_credentials.Path.home")
    @patch.dict(os.environ, {"SSH_AUTH_SOCK": "/tmp/ssh-agent"}, clear=True)
    @patch(
        "git.provider.credential_manager.create_auth"
    )
    def test_get_auth_for_provider_github_success(
        self, mock_create_auth, mock_home
    ) -> None:
        """Test get_auth_for_provider returns SSH auth for GitHub."""
        mock_home.return_value = Path("/tmp")
        manager = CredentialManager()
        mock_auth = MagicMock(spec=HttpAuthBase)
        mock_create_auth.return_value = mock_auth

        result = manager.get_auth_for_provider("github")

        assert result is not None
        assert isinstance(result, HttpAuthBase)
        mock_create_auth.assert_called_once_with(
            "ssh", username="git", use_agent=True
        )

    @patch("credentials.ssh_credentials.Path.home")
    @patch.dict(os.environ, {}, clear=True)
    def test_get_auth_for_provider_github_no_credentials(self, mock_home) -> None:
        """Test get_auth_for_provider returns None for GitHub without SSH credentials."""
        mock_home.return_value = Path("/empty/home")
        manager = CredentialManager()

        result = manager.get_auth_for_provider("github")

        assert result is None

    @patch.dict(os.environ, {"SSH_AUTH_SOCK": "/tmp/ssh-agent"}, clear=True)
    @patch(
        "git.provider.credential_manager.create_auth"
    )
    def test_get_auth_for_provider_github_import_error(self, mock_create_auth) -> None:
        """Test get_auth_for_provider handles ImportError gracefully for GitHub."""
        manager = CredentialManager()
        mock_create_auth.side_effect = ImportError("Module not found")

        result = manager.get_auth_for_provider("github")

        assert result is None

    @patch("credentials.ssh_credentials.Path.home")
    @patch.dict(os.environ, {"SSH_AUTH_SOCK": "/tmp/ssh-agent"}, clear=True)
    @patch(
        "git.provider.credential_manager.create_auth"
    )
    def test_get_auth_for_provider_bitbucket_success(
        self, mock_create_auth, mock_home
    ) -> None:
        """Test get_auth_for_provider returns SSH auth for Bitbucket."""
        mock_home.return_value = Path("/tmp")
        manager = CredentialManager()
        mock_auth = MagicMock(spec=HttpAuthBase)
        mock_create_auth.return_value = mock_auth

        result = manager.get_auth_for_provider("bitbucket")

        assert result is not None
        assert isinstance(result, HttpAuthBase)
        mock_create_auth.assert_called_once_with(
            "ssh", username="git", use_agent=True
        )

    @patch("credentials.ssh_credentials.Path.home")
    @patch.dict(os.environ, {}, clear=True)
    def test_get_auth_for_provider_bitbucket_no_credentials(self, mock_home) -> None:
        """Test get_auth_for_provider returns None for Bitbucket without SSH credentials."""
        mock_home.return_value = Path("/empty/home")
        manager = CredentialManager()

        result = manager.get_auth_for_provider("bitbucket")

        assert result is None

    @patch.dict(os.environ, {"SSH_AUTH_SOCK": "/tmp/ssh-agent"}, clear=True)
    @patch(
        "git.provider.credential_manager.create_auth"
    )
    def test_get_auth_for_provider_bitbucket_import_error(
        self, mock_create_auth
    ) -> None:
        """Test get_auth_for_provider handles ImportError gracefully for Bitbucket."""
        manager = CredentialManager()
        mock_create_auth.side_effect = ImportError("Module not found")

        result = manager.get_auth_for_provider("bitbucket")

        assert result is None

    @patch.dict(os.environ, {}, clear=True)
    def test_get_auth_for_provider_unknown(self) -> None:
        """Test get_auth_for_provider returns None for unknown provider."""
        manager = CredentialManager()

        result = manager.get_auth_for_provider("unknown")

        assert result is None

    @patch("credentials.ssh_credentials.Path.home")
    @patch.dict(
        os.environ,
        {
            "NEXUS_USERNAME": "test_user",
            "NEXUS_PASSWORD": "test_pass",
        },
        clear=True,
    )
    def test_get_available_providers_some_available(self, mock_home) -> None:
        """Test get_available_providers returns only providers with available credentials."""
        mock_home.return_value = Path("/empty/home")
        manager = CredentialManager()
        available = manager.get_available_providers()
        assert "storage" in available
        assert "github" not in available
        assert "bitbucket" not in available

    @patch.dict(
        os.environ,
        {
            "NEXUS_USERNAME": "test_user",
            "NEXUS_PASSWORD": "test_pass",
            "SSH_AUTH_SOCK": "/tmp/ssh-agent",
        },
    )
    def test_get_available_providers_all_available(self) -> None:
        """Test get_available_providers returns all providers when all credentials are available."""
        manager = CredentialManager()
        available = manager.get_available_providers()
        assert "storage" in available
        assert "github" in available
        assert "bitbucket" in available

    @patch("credentials.ssh_credentials.Path.home")
    @patch.dict(os.environ, {}, clear=True)
    def test_get_available_providers_none_available(self, mock_home) -> None:
        """Test get_available_providers returns empty list when no credentials are available."""
        mock_home.return_value = Path("/empty/home")
        manager = CredentialManager()
        available = manager.get_available_providers()
        assert available == []

    @patch.dict(os.environ, {}, clear=True)
    def test_get_missing_credentials_info_nexus_missing_all(self) -> None:
        """Test get_missing_credentials_info returns all missing Nexus credentials."""
        manager = CredentialManager()
        result = manager.get_missing_credentials_info("storage")
        assert "NEXUS_USERNAME" in result
        assert "NEXUS_PASSWORD" in result
        assert len(result) == 2

    @patch.dict(os.environ, {"NEXUS_USERNAME": "test_user"}, clear=True)
    def test_get_missing_credentials_info_nexus_missing_password(self) -> None:
        """Test get_missing_credentials_info returns only missing Nexus password."""
        manager = CredentialManager()
        result = manager.get_missing_credentials_info("storage")
        assert "NEXUS_USERNAME" not in result
        assert "NEXUS_PASSWORD" in result
        assert len(result) == 1

    @patch.dict(
        os.environ, {"NEXUS_USERNAME": "test_user", "NEXUS_PASSWORD": "test_pass"}
    )
    def test_get_missing_credentials_info_nexus_none_missing(self) -> None:
        """Test get_missing_credentials_info returns empty list when all Nexus credentials are available."""
        manager = CredentialManager()
        result = manager.get_missing_credentials_info("storage")
        assert result == []

    @patch("credentials.ssh_credentials.Path.home")
    @patch.dict(os.environ, {}, clear=True)
    def test_get_missing_credentials_info_github_missing(self, mock_home) -> None:
        """Test get_missing_credentials_info returns missing SSH credentials."""
        mock_home.return_value = Path("/empty/home")
        manager = CredentialManager()
        result = manager.get_missing_credentials_info("github")
        assert "SSH private key" in result[0]
        assert len(result) == 1

    @patch.dict(os.environ, {"SSH_AUTH_SOCK": "/tmp/ssh-agent"}, clear=True)
    def test_get_missing_credentials_info_github_none_missing(self) -> None:
        """Test get_missing_credentials_info returns empty list when SSH agent is available."""
        manager = CredentialManager()
        result = manager.get_missing_credentials_info("github")
        assert result == []

    @patch("credentials.ssh_credentials.Path.home")
    @patch.dict(os.environ, {}, clear=True)
    def test_get_missing_credentials_info_bitbucket_missing_all(self, mock_home) -> None:
        """Test get_missing_credentials_info returns missing SSH credentials."""
        mock_home.return_value = Path("/empty/home")
        manager = CredentialManager()
        result = manager.get_missing_credentials_info("bitbucket")
        assert "SSH private key" in result[0]
        assert len(result) == 1

    @patch.dict(os.environ, {}, clear=True)
    def test_get_missing_credentials_info_unknown_provider(self) -> None:
        """Test get_missing_credentials_info returns error message for unknown provider."""
        manager = CredentialManager()
        result = manager.get_missing_credentials_info("unknown")
        assert result == ["Unknown provider: unknown"]

    @patch("git.provider.credential_manager.log")
    def test_get_auth_for_provider_unknown_provider_warning(self, mock_log) -> None:
        """Test get_auth_for_provider logs warning for unknown provider."""
        manager = CredentialManager()

        result = manager.get_auth_for_provider("unknown")

        assert result is None
        mock_log.warning.assert_called_with("Unknown provider: %s", "unknown")

    @patch("git.provider.credential_manager.log")
    def test_get_auth_for_provider_unknown_provider_warning_second_call(
        self, mock_log
    ) -> None:
        """Test get_auth_for_provider logs warning for unknown provider in _create_auth_object."""
        manager = CredentialManager()

        # First call to has_credentials will return False, but we need to test the second call
        # where provider_config is None in _create_auth_object
        with patch.object(manager, "has_credentials", return_value=True):
            with patch.object(
                ProvidersConfig, "get_provider_config", return_value=None
            ):
                result = manager.get_auth_for_provider("unknown")

        assert result is None
        mock_log.warning.assert_called_with("Unknown provider: %s", "unknown")

    def test_docstring_contains_expected_content(self) -> None:
        """Test that the class docstring contains expected content."""
        docstring = CredentialManager.__doc__
        assert docstring is not None
        assert "authentication" in docstring.lower()
        assert "credentials" in docstring.lower()
        assert "environment" in docstring.lower()
