"""Tests for versioner factory module."""

from unittest.mock import MagicMock, patch

import pytest

from kbot_installer.core.versioner.factory import create_versioner
from kbot_installer.core.versioner.versioner_base import VersionerBase


class TestCreateVersioner:
    """Test cases for create_versioner function."""

    def test_create_versioner_pygit_success(self) -> None:
        """Test creating PygitVersioner successfully."""
        with patch(
            "kbot_installer.core.versioner.factory.factory_method"
        ) as mock_factory_method:
            # Mock the factory method to return a mock versioner
            mock_versioner = MagicMock(spec=VersionerBase)
            mock_factory_method.return_value = mock_versioner

            result = create_versioner("pygit", auth=None)

            # Verify factory_method was called with correct arguments
            mock_factory_method.assert_called_once_with(
                "pygit", "kbot_installer.core.versioner", auth=None
            )
            assert result == mock_versioner

    def test_create_versioner_gitpython_success(self) -> None:
        """Test creating GitPythonVersioner successfully."""
        with patch(
            "kbot_installer.core.versioner.factory.factory_method"
        ) as mock_factory_method:
            # Mock the factory method to return a mock versioner
            mock_versioner = MagicMock(spec=VersionerBase)
            mock_factory_method.return_value = mock_versioner

            result = create_versioner("gitpython", auth="test_auth")

            # Verify factory_method was called with correct arguments
            mock_factory_method.assert_called_once_with(
                "gitpython", "kbot_installer.core.versioner", auth="test_auth"
            )
            assert result == mock_versioner

    def test_create_versioner_nexus_success(self) -> None:
        """Test creating NexusVersioner successfully."""
        with patch(
            "kbot_installer.core.versioner.factory.factory_method"
        ) as mock_factory_method:
            # Mock the factory method to return a mock versioner
            mock_versioner = MagicMock(spec=VersionerBase)
            mock_factory_method.return_value = mock_versioner

            result = create_versioner("nexus", base_url="https://nexus.example.com")

            # Verify factory_method was called with correct arguments
            mock_factory_method.assert_called_once_with(
                "nexus",
                "kbot_installer.core.versioner",
                base_url="https://nexus.example.com",
            )
            assert result == mock_versioner

    def test_create_versioner_with_multiple_kwargs(self) -> None:
        """Test creating versioner with multiple keyword arguments."""
        with patch(
            "kbot_installer.core.versioner.factory.factory_method"
        ) as mock_factory_method:
            # Mock the factory method to return a mock versioner
            mock_versioner = MagicMock(spec=VersionerBase)
            mock_factory_method.return_value = mock_versioner

            kwargs = {"auth": "test_auth", "timeout": 30, "retries": 3}

            result = create_versioner("pygit", **kwargs)

            # Verify factory_method was called with all kwargs
            mock_factory_method.assert_called_once_with(
                "pygit", "kbot_installer.core.versioner", **kwargs
            )
            assert result == mock_versioner

    def test_create_versioner_with_no_kwargs(self) -> None:
        """Test creating versioner with no keyword arguments."""
        with patch(
            "kbot_installer.core.versioner.factory.factory_method"
        ) as mock_factory_method:
            # Mock the factory method to return a mock versioner
            mock_versioner = MagicMock(spec=VersionerBase)
            mock_factory_method.return_value = mock_versioner

            result = create_versioner("pygit")

            # Verify factory_method was called with only name and package
            mock_factory_method.assert_called_once_with(
                "pygit", "kbot_installer.core.versioner"
            )
            assert result == mock_versioner

    def test_create_versioner_import_error(self) -> None:
        """Test handling of ImportError from factory_method."""
        with patch(
            "kbot_installer.core.versioner.factory.factory_method"
        ) as mock_factory_method:
            # Mock factory_method to raise ImportError
            mock_factory_method.side_effect = ImportError("Cannot import module")

            with pytest.raises(ImportError, match="Cannot import module"):
                create_versioner("nonexistent")

    def test_create_versioner_attribute_error(self) -> None:
        """Test handling of AttributeError from factory_method."""
        with patch(
            "kbot_installer.core.versioner.factory.factory_method"
        ) as mock_factory_method:
            # Mock factory_method to raise AttributeError
            mock_factory_method.side_effect = AttributeError("Class not found")

            with pytest.raises(AttributeError, match="Class not found"):
                create_versioner("invalid")

    def test_create_versioner_type_error(self) -> None:
        """Test handling of TypeError from factory_method."""
        with patch(
            "kbot_installer.core.versioner.factory.factory_method"
        ) as mock_factory_method:
            # Mock factory_method to raise TypeError
            mock_factory_method.side_effect = TypeError("Invalid arguments")

            with pytest.raises(TypeError, match="Invalid arguments"):
                create_versioner("pygit", invalid_arg="test")

    def test_create_versioner_passes_through_exceptions(self) -> None:
        """Test that create_versioner passes through all exceptions from factory_method."""
        with patch(
            "kbot_installer.core.versioner.factory.factory_method"
        ) as mock_factory_method:
            # Test various exception types
            exceptions = [
                ValueError("Value error"),
                RuntimeError("Runtime error"),
                KeyError("Key error"),
                FileNotFoundError("File not found"),
            ]

            for exception in exceptions:
                mock_factory_method.side_effect = exception

                with pytest.raises(type(exception), match=str(exception)):
                    create_versioner("pygit")

    def test_create_versioner_function_signature(self) -> None:
        """Test that create_versioner has the correct function signature."""
        import inspect

        sig = inspect.signature(create_versioner)
        params = list(sig.parameters.keys())

        # Should have 'name' as first parameter and **kwargs
        assert "name" in params
        assert sig.parameters["name"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD

        # Should accept **kwargs
        assert any(
            p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
        )

    def test_create_versioner_docstring_example(self) -> None:
        """Test the example from the docstring works correctly."""
        with patch(
            "kbot_installer.core.versioner.factory.factory_method"
        ) as mock_factory_method:
            # Mock the factory method to return a mock versioner
            mock_versioner = MagicMock(spec=VersionerBase)
            mock_versioner.__str__ = MagicMock(return_value="PygitVersioner()")
            mock_factory_method.return_value = mock_versioner

            # Test the example from docstring
            versioner = create_versioner("pygit", auth="test_auth")
            result = str(versioner)

            # Verify the example works
            assert result == "PygitVersioner()"
            mock_factory_method.assert_called_once_with(
                "pygit", "kbot_installer.core.versioner", auth="test_auth"
            )

    def test_create_versioner_with_none_values(self) -> None:
        """Test creating versioner with None values in kwargs."""
        with patch(
            "kbot_installer.core.versioner.factory.factory_method"
        ) as mock_factory_method:
            # Mock the factory method to return a mock versioner
            mock_versioner = MagicMock(spec=VersionerBase)
            mock_factory_method.return_value = mock_versioner

            kwargs = {"auth": None, "timeout": None}

            result = create_versioner("pygit", **kwargs)

            # Verify factory_method was called with None values
            mock_factory_method.assert_called_once_with(
                "pygit", "kbot_installer.core.versioner", **kwargs
            )
            assert result == mock_versioner

    def test_create_versioner_with_empty_string(self) -> None:
        """Test creating versioner with empty string name."""
        with patch(
            "kbot_installer.core.versioner.factory.factory_method"
        ) as mock_factory_method:
            # Mock the factory method to return a mock versioner
            mock_versioner = MagicMock(spec=VersionerBase)
            mock_factory_method.return_value = mock_versioner

            result = create_versioner("")

            # Verify factory_method was called with empty string
            mock_factory_method.assert_called_once_with(
                "", "kbot_installer.core.versioner"
            )
            assert result == mock_versioner

    def test_create_versioner_with_special_characters(self) -> None:
        """Test creating versioner with special characters in name."""
        with patch(
            "kbot_installer.core.versioner.factory.factory_method"
        ) as mock_factory_method:
            # Mock the factory method to return a mock versioner
            mock_versioner = MagicMock(spec=VersionerBase)
            mock_factory_method.return_value = mock_versioner

            special_name = "test-versioner_123"
            result = create_versioner(special_name)

            # Verify factory_method was called with special characters
            mock_factory_method.assert_called_once_with(
                special_name, "kbot_installer.core.versioner"
            )
            assert result == mock_versioner
