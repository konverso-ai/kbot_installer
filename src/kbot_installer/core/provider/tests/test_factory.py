"""Tests for factory module."""

from unittest.mock import MagicMock, patch

import pytest

from kbot_installer.core.provider.factory import create_provider
from kbot_installer.core.provider.provider_base import ProviderBase


class TestCreateProvider:
    """Test cases for create_provider function."""

    def test_create_provider_nexus(self) -> None:
        """Test creating nexus provider."""
        with patch(
            "kbot_installer.core.provider.factory.factory_method"
        ) as mock_factory:
            mock_provider = MagicMock(spec=ProviderBase)
            mock_factory.return_value = mock_provider

            result = create_provider("nexus", domain="test.com", repository="test")

            mock_factory.assert_called_once_with(
                "nexus",
                "kbot_installer.core.provider",
                domain="test.com",
                repository="test",
            )
            assert result is mock_provider

    def test_create_provider_github(self) -> None:
        """Test creating github provider."""
        with patch(
            "kbot_installer.core.provider.factory.factory_method"
        ) as mock_factory:
            mock_provider = MagicMock(spec=ProviderBase)
            mock_factory.return_value = mock_provider

            result = create_provider("github", account_name="test")

            mock_factory.assert_called_once_with(
                "github", "kbot_installer.core.provider", account_name="test"
            )
            assert result is mock_provider

    def test_create_provider_bitbucket(self) -> None:
        """Test creating bitbucket provider."""
        with patch(
            "kbot_installer.core.provider.factory.factory_method"
        ) as mock_factory:
            mock_provider = MagicMock(spec=ProviderBase)
            mock_factory.return_value = mock_provider

            result = create_provider("bitbucket", account_name="test")

            mock_factory.assert_called_once_with(
                "bitbucket", "kbot_installer.core.provider", account_name="test"
            )
            assert result is mock_provider

    def test_create_provider_handles_import_error(self) -> None:
        """Test that create_provider handles ImportError."""
        with patch(
            "kbot_installer.core.provider.factory.factory_method"
        ) as mock_factory:
            mock_factory.side_effect = ImportError("Module not found")

            with pytest.raises(ImportError, match="Module not found"):
                create_provider("unknown", test="value")

    def test_create_provider_handles_attribute_error(self) -> None:
        """Test that create_provider handles AttributeError."""
        with patch(
            "kbot_installer.core.provider.factory.factory_method"
        ) as mock_factory:
            mock_factory.side_effect = AttributeError("Class not found")

            with pytest.raises(AttributeError, match="Class not found"):
                create_provider("unknown", test="value")

    def test_create_provider_handles_type_error(self) -> None:
        """Test that create_provider handles TypeError."""
        with patch(
            "kbot_installer.core.provider.factory.factory_method"
        ) as mock_factory:
            mock_factory.side_effect = TypeError("Invalid arguments")

            with pytest.raises(TypeError, match="Invalid arguments"):
                create_provider("unknown", test="value")

    def test_create_provider_with_no_kwargs(self) -> None:
        """Test creating provider with no additional arguments."""
        with patch(
            "kbot_installer.core.provider.factory.factory_method"
        ) as mock_factory:
            mock_provider = MagicMock(spec=ProviderBase)
            mock_factory.return_value = mock_provider

            result = create_provider("nexus")

            mock_factory.assert_called_once_with(
                "nexus", "kbot_installer.core.provider"
            )
            assert result is mock_provider
