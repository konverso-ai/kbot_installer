"""Tests for factory module."""

from unittest.mock import MagicMock, patch

import pytest

from git.provider.base import ProviderBase
from git.provider.factory import (
    add_provider,
    add_transport_provider,
    basic_bitbucket_provider,
    basic_github_provider,
    ssh_bitbucket_provider,
    ssh_github_provider,
)


class TestCreateProvider:
    """Test cases for add_provider function."""

    def test_add_provider_storage(self) -> None:
        """Test creating storage provider."""
        with patch("git.provider.factory.factory_method") as mock_factory_method:
            mock_provider = MagicMock(spec=ProviderBase)
            mock_factory_method.return_value = mock_provider

            result = add_provider("storage")

            mock_factory_method.assert_called_once_with(
                "storage",
                "git.provider",
            )
            assert result is mock_provider

    def test_add_provider_github(self) -> None:
        """Test creating github provider."""
        with patch(
            "git.provider.factory.factory_method"
        ) as mock_factory:
            mock_provider = MagicMock(spec=ProviderBase)
            mock_factory.return_value = mock_provider

            result = add_provider("github", account_name="test")

            mock_factory.assert_called_once_with(
                "github", "git.provider", account_name="test"
            )
            assert result is mock_provider

    def test_add_provider_bitbucket(self) -> None:
        """Test creating bitbucket provider."""
        with patch(
            "git.provider.factory.factory_method"
        ) as mock_factory:
            mock_provider = MagicMock(spec=ProviderBase)
            mock_factory.return_value = mock_provider

            result = add_provider("bitbucket", account_name="test")

            mock_factory.assert_called_once_with(
                "bitbucket", "git.provider", account_name="test"
            )
            assert result is mock_provider

    def test_add_provider_handles_import_error(self) -> None:
        """Test that add_provider handles ImportError."""
        with patch(
            "git.provider.factory.factory_method"
        ) as mock_factory:
            mock_factory.side_effect = ImportError("Module not found")

            with pytest.raises(ImportError, match="Module not found"):
                add_provider("unknown", test="value")

    def test_add_provider_handles_attribute_error(self) -> None:
        """Test that add_provider handles AttributeError."""
        with patch(
            "git.provider.factory.factory_method"
        ) as mock_factory:
            mock_factory.side_effect = AttributeError("Class not found")

            with pytest.raises(AttributeError, match="Class not found"):
                add_provider("unknown", test="value")

    def test_add_provider_handles_type_error(self) -> None:
        """Test that add_provider handles TypeError."""
        with patch(
            "git.provider.factory.factory_method"
        ) as mock_factory:
            mock_factory.side_effect = TypeError("Invalid arguments")

            with pytest.raises(TypeError, match="Invalid arguments"):
                add_provider("unknown", test="value")

    def test_add_provider_with_no_kwargs(self) -> None:
        """Test creating provider with no additional arguments."""
        with patch(
            "git.provider.factory.factory_method"
        ) as mock_factory:
            mock_provider = MagicMock(spec=ProviderBase)
            mock_factory.return_value = mock_provider

            result = add_provider("storage")

            mock_factory.assert_called_once_with(
                "storage", "git.provider"
            )
            assert result is mock_provider


class TestSshGithubProvider:
    """Test cases for ssh_github_provider function."""

    def test_builds_provider_with_ssh_auth(self) -> None:
        """Test that it builds a github provider using SSH credentials/auth."""
        mock_credentials = MagicMock()
        mock_credentials.auth_kwargs.return_value = {"key": "value"}
        mock_auth = MagicMock()
        mock_provider = MagicMock(spec=ProviderBase)

        with (
            patch(
                "git.provider.factory.SshGithubCredentials",
                return_value=mock_credentials,
            ),
            patch(
                "git.provider.factory.add_ssh_auth", return_value=mock_auth
            ) as mock_add_ssh_auth,
            patch(
                "git.provider.factory.add_provider", return_value=mock_provider
            ) as mock_add_provider,
        ):
            result = ssh_github_provider()

            mock_credentials.auth_kwargs.assert_called_once_with()
            mock_add_ssh_auth.assert_called_once_with(name="ssh", key="value")
            mock_add_provider.assert_called_once_with(
                name="github", auth=mock_auth
            )
            assert result is mock_provider


class TestSshBitbucketProvider:
    """Test cases for ssh_bitbucket_provider function."""

    def test_builds_provider_with_ssh_auth(self) -> None:
        """Test that it builds a bitbucket provider using SSH credentials/auth."""
        mock_credentials = MagicMock()
        mock_credentials.auth_kwargs.return_value = {"key": "value"}
        mock_auth = MagicMock()
        mock_provider = MagicMock(spec=ProviderBase)

        with (
            patch(
                "git.provider.factory.SshBitbucketCredentials",
                return_value=mock_credentials,
            ),
            patch(
                "git.provider.factory.add_ssh_auth", return_value=mock_auth
            ) as mock_add_ssh_auth,
            patch(
                "git.provider.factory.add_provider", return_value=mock_provider
            ) as mock_add_provider,
        ):
            result = ssh_bitbucket_provider()

            mock_credentials.auth_kwargs.assert_called_once_with()
            mock_add_ssh_auth.assert_called_once_with(name="ssh", key="value")
            mock_add_provider.assert_called_once_with(
                name="bitbucket", auth=mock_auth
            )
            assert result is mock_provider


class TestBasicGithubProvider:
    """Test cases for basic_github_provider function."""

    def test_builds_provider_with_basic_auth(self) -> None:
        """Test that it builds a github provider using basic credentials/auth."""
        mock_credentials = MagicMock()
        mock_credentials.auth_kwargs.return_value = {"key": "value"}
        mock_auth = MagicMock()
        mock_provider = MagicMock(spec=ProviderBase)

        with (
            patch(
                "git.provider.factory.BasicGithubCredentials",
                return_value=mock_credentials,
            ),
            patch(
                "git.provider.factory.add_http_auth", return_value=mock_auth
            ) as mock_add_http_auth,
            patch(
                "git.provider.factory.add_provider", return_value=mock_provider
            ) as mock_add_provider,
        ):
            result = basic_github_provider()

            mock_credentials.auth_kwargs.assert_called_once_with()
            mock_add_http_auth.assert_called_once_with(name="basic", key="value")
            mock_add_provider.assert_called_once_with(
                name="github", auth=mock_auth
            )
            assert result is mock_provider


class TestBasicBitbucketProvider:
    """Test cases for basic_bitbucket_provider function."""

    def test_builds_provider_with_basic_auth(self) -> None:
        """Test that it builds a bitbucket provider using basic credentials/auth."""
        mock_credentials = MagicMock()
        mock_credentials.auth_kwargs.return_value = {"key": "value"}
        mock_auth = MagicMock()
        mock_provider = MagicMock(spec=ProviderBase)

        with (
            patch(
                "git.provider.factory.BasicBitbucketCredentials",
                return_value=mock_credentials,
            ),
            patch(
                "git.provider.factory.add_http_auth", return_value=mock_auth
            ) as mock_add_http_auth,
            patch(
                "git.provider.factory.add_provider", return_value=mock_provider
            ) as mock_add_provider,
        ):
            result = basic_bitbucket_provider()

            mock_credentials.auth_kwargs.assert_called_once_with()
            mock_add_http_auth.assert_called_once_with(name="basic", key="value")
            mock_add_provider.assert_called_once_with(
                name="bitbucket", auth=mock_auth
            )
            assert result is mock_provider


class TestAddTransportProvider:
    """Test cases for add_transport_provider function."""

    def test_dispatches_to_matching_builder(self) -> None:
        """Test that it resolves and calls the {transport}_{provider}_provider function."""
        mock_provider = MagicMock(spec=ProviderBase)
        mock_builder = MagicMock(return_value=mock_provider)

        with patch(
            "git.provider.factory.factory_function", return_value=mock_builder
        ) as mock_factory_function:
            result = add_transport_provider("ssh", "github")

            mock_factory_function.assert_called_once_with(
                module_name="git.provider.factory",
                attribute_name="ssh_github_provider",
            )
            mock_builder.assert_called_once_with()
            assert result is mock_provider

    def test_propagates_attribute_error_when_builder_missing(self) -> None:
        """Test that it propagates AttributeError when no matching builder exists."""
        with patch(
            "git.provider.factory.factory_function",
            side_effect=AttributeError("No such attribute"),
        ):
            with pytest.raises(AttributeError, match="No such attribute"):
                add_transport_provider("unknown", "unknown")
