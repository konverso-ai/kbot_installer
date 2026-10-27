"""Tests for versioner factory module."""

from unittest.mock import MagicMock, patch

import pytest

from git.versioner.factory import add_versioner
from git.versioner.base import VersionerBase


class TestCreateVersioner:
    """Test cases for add_versioner function."""

    def test_add_versioner_dulwich_success(self) -> None:
        """Test creating DulwichVersioner successfully."""
        with patch(
            "git.versioner.factory.factory_method"
        ) as mock_factory_method:
            # Mock the factory method to return a mock versioner
            mock_versioner = MagicMock(spec=VersionerBase)
            mock_factory_method.return_value = mock_versioner

            result = add_versioner("dulwich", auth=None)

            # Verify factory_method was called with correct arguments
            mock_factory_method.assert_called_once_with(
                "dulwich", "git.versioner", auth=None
            )
            assert result == mock_versioner

    def test_add_versioner_gitpython_success(self) -> None:
        """Test creating GitPythonVersioner successfully."""
        with patch(
            "git.versioner.factory.factory_method"
        ) as mock_factory_method:
            # Mock the factory method to return a mock versioner
            mock_versioner = MagicMock(spec=VersionerBase)
            mock_factory_method.return_value = mock_versioner

            result = add_versioner("gitpython", auth="test_auth")

            # Verify factory_method was called with correct arguments
            mock_factory_method.assert_called_once_with(
                "gitpython", "git.versioner", auth="test_auth"
            )
            assert result == mock_versioner

    def test_add_versioner_with_multiple_kwargs(self) -> None:
        """Test creating versioner with multiple keyword arguments."""
        with patch(
            "git.versioner.factory.factory_method"
        ) as mock_factory_method:
            # Mock the factory method to return a mock versioner
            mock_versioner = MagicMock(spec=VersionerBase)
            mock_factory_method.return_value = mock_versioner

            kwargs = {"auth": "test_auth", "timeout": 30, "retries": 3}

            result = add_versioner("dulwich", **kwargs)

            # Verify factory_method was called with all kwargs
            mock_factory_method.assert_called_once_with(
                "dulwich", "git.versioner", **kwargs
            )
            assert result == mock_versioner

    def test_add_versioner_with_no_kwargs(self) -> None:
        """Test creating versioner with no keyword arguments."""
        with patch(
            "git.versioner.factory.factory_method"
        ) as mock_factory_method:
            # Mock the factory method to return a mock versioner
            mock_versioner = MagicMock(spec=VersionerBase)
            mock_factory_method.return_value = mock_versioner

            result = add_versioner("dulwich")

            # Verify factory_method was called with only name and package
            mock_factory_method.assert_called_once_with(
                "dulwich", "git.versioner"
            )
            assert result == mock_versioner

    def test_add_versioner_import_error(self) -> None:
        """Test handling of ImportError from factory_method."""
        with patch(
            "git.versioner.factory.factory_method"
        ) as mock_factory_method:
            # Mock factory_method to raise ImportError
            mock_factory_method.side_effect = ImportError("Cannot import module")

            with pytest.raises(ImportError, match="Cannot import module"):
                add_versioner("nonexistent")

    def test_add_versioner_attribute_error(self) -> None:
        """Test handling of AttributeError from factory_method."""
        with patch(
            "git.versioner.factory.factory_method"
        ) as mock_factory_method:
            # Mock factory_method to raise AttributeError
            mock_factory_method.side_effect = AttributeError("Class not found")

            with pytest.raises(AttributeError, match="Class not found"):
                add_versioner("invalid")

    def test_add_versioner_type_error(self) -> None:
        """Test handling of TypeError from factory_method."""
        with patch(
            "git.versioner.factory.factory_method"
        ) as mock_factory_method:
            # Mock factory_method to raise TypeError
            mock_factory_method.side_effect = TypeError("Invalid arguments")

            with pytest.raises(TypeError, match="Invalid arguments"):
                add_versioner("dulwich", invalid_arg="test")

    def test_add_versioner_passes_through_exceptions(self) -> None:
        """Test that add_versioner passes through all exceptions from factory_method."""
        with patch(
            "git.versioner.factory.factory_method"
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
                    add_versioner("dulwich")

    def test_add_versioner_function_signature(self) -> None:
        """Test that add_versioner has the correct function signature."""
        import inspect

        sig = inspect.signature(add_versioner)
        params = list(sig.parameters.keys())

        # Should have 'name' as first parameter and **kwargs
        assert "name" in params
        assert sig.parameters["name"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD

        # Should accept **kwargs
        assert any(
            p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
        )

    def test_add_versioner_docstring_example(self) -> None:
        """Test the example from the docstring works correctly."""
        with patch(
            "git.versioner.factory.factory_method"
        ) as mock_factory_method:
            # Mock the factory method to return a mock versioner
            mock_versioner = MagicMock(spec=VersionerBase)
            mock_versioner.__str__ = MagicMock(return_value="DulwichVersioner()")
            mock_factory_method.return_value = mock_versioner

            # Test the example from docstring
            versioner = add_versioner("dulwich", auth="test_auth")
            result = str(versioner)

            # Verify the example works
            assert result == "DulwichVersioner()"
            mock_factory_method.assert_called_once_with(
                "dulwich", "git.versioner", auth="test_auth"
            )

    def test_add_versioner_with_none_values(self) -> None:
        """Test creating versioner with None values in kwargs."""
        with patch(
            "git.versioner.factory.factory_method"
        ) as mock_factory_method:
            # Mock the factory method to return a mock versioner
            mock_versioner = MagicMock(spec=VersionerBase)
            mock_factory_method.return_value = mock_versioner

            kwargs = {"auth": None, "timeout": None}

            result = add_versioner("dulwich", **kwargs)

            # Verify factory_method was called with None values
            mock_factory_method.assert_called_once_with(
                "dulwich", "git.versioner", **kwargs
            )
            assert result == mock_versioner

    def test_add_versioner_with_empty_string(self) -> None:
        """Test creating versioner with empty string name."""
        with patch(
            "git.versioner.factory.factory_method"
        ) as mock_factory_method:
            # Mock the factory method to return a mock versioner
            mock_versioner = MagicMock(spec=VersionerBase)
            mock_factory_method.return_value = mock_versioner

            result = add_versioner("")

            # Verify factory_method was called with empty string
            mock_factory_method.assert_called_once_with(
                "", "git.versioner"
            )
            assert result == mock_versioner

    def test_add_versioner_with_special_characters(self) -> None:
        """Test creating versioner with special characters in name."""
        with patch(
            "git.versioner.factory.factory_method"
        ) as mock_factory_method:
            # Mock the factory method to return a mock versioner
            mock_versioner = MagicMock(spec=VersionerBase)
            mock_factory_method.return_value = mock_versioner

            special_name = "test-versioner_123"
            result = add_versioner(special_name)

            # Verify factory_method was called with special characters
            mock_factory_method.assert_called_once_with(
                special_name, "git.versioner"
            )
            assert result == mock_versioner
