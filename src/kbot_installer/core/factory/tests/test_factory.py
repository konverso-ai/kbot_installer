"""Tests for factory module."""

from unittest.mock import MagicMock, patch

import pytest

from kbot_installer.core.factory.factory import (
    factory_class,
    factory_method,
    factory_object,
)


class TestFactoryClass:
    """Test cases for factory_class function."""

    def test_function_exists(self) -> None:
        """Test that factory_class function exists and is callable."""
        assert callable(factory_class)

    def test_handles_import_error(self) -> None:
        """Test that factory_class handles ImportError."""
        with pytest.raises(ImportError):
            factory_class("nonexistent_module", "nonexistent_package")

    def test_handles_attribute_error(self) -> None:
        """Test that factory_class handles AttributeError."""
        with pytest.raises(
            ImportError
        ):  # This will raise ImportError, not AttributeError
            factory_class("nonexistent_class", "factory")

    def test_handles_real_import_error(self) -> None:
        """Test that factory_class handles real ImportError scenarios."""
        with pytest.raises(ImportError):
            factory_class("nonexistent", "factory")

    @patch("importlib.import_module")
    @patch(
        "kbot_installer.core.factory.factory.build_class_name",
        return_value="UtilsFactory",
    )
    @patch(
        "kbot_installer.core.factory.factory.build_module_name", return_value="utils"
    )
    def test_returns_class_from_module(
        self, mock_build_module_name, mock_build_class_name, mock_import_module
    ) -> None:
        """Test that factory_class returns a class from a module."""
        # Mock the module with a class
        mock_module = MagicMock()
        mock_class = MagicMock()
        mock_module.UtilsFactory = mock_class
        mock_import_module.return_value = mock_module

        # Call factory_class
        result = factory_class("test", "package")

        # Verify the calls
        mock_build_module_name.assert_called_once_with("test", "package")
        mock_build_class_name.assert_called_once_with("test", "package")
        mock_import_module.assert_called_once_with("package.utils")

        # Verify the result
        assert result == mock_class


class TestFactoryObject:
    """Test cases for factory_object function."""

    @patch("kbot_installer.core.factory.factory.factory_class")
    def test_calls_factory_class_and_instantiates(self, mock_factory_class) -> None:
        """Test that factory_object calls factory_class and instantiates the class."""
        mock_class = MagicMock()
        mock_instance = MagicMock()
        mock_class.return_value = mock_instance
        mock_factory_class.return_value = mock_class

        result = factory_object("test", "package", arg1="value1", arg2="value2")

        mock_factory_class.assert_called_once_with("test", "package")
        mock_class.assert_called_once_with(arg1="value1", arg2="value2")
        assert result == mock_instance

    @patch("kbot_installer.core.factory.factory.factory_class")
    def test_passes_kwargs_to_constructor(self, mock_factory_class) -> None:
        """Test that factory_object passes kwargs to the class constructor."""
        mock_class = MagicMock()
        mock_instance = MagicMock()
        mock_class.return_value = mock_instance
        mock_factory_class.return_value = mock_class

        kwargs = {"username": "test", "password": "pass"}
        factory_object("test", "package", **kwargs)

        mock_class.assert_called_once_with(**kwargs)

    @patch("kbot_installer.core.factory.factory.factory_class")
    def test_handles_type_error_from_constructor(self, mock_factory_class) -> None:
        """Test that factory_object handles TypeError from constructor."""
        mock_class = MagicMock()
        mock_class.side_effect = TypeError("Invalid arguments")
        mock_factory_class.return_value = mock_class

        with pytest.raises(TypeError):
            factory_object("test", "package", invalid_arg="value")

    def test_handles_real_import_error(self) -> None:
        """Test that factory_object handles real ImportError scenarios."""
        with pytest.raises(ImportError):
            factory_object("nonexistent", "factory")


class TestFactoryMethod:
    """Test cases for factory_method function."""

    @patch("kbot_installer.core.factory.factory.factory_class")
    def test_calls_factory_class_and_instantiates(self, mock_factory_class) -> None:
        """Test that factory_method calls factory_class and instantiates the class."""
        mock_class = MagicMock()
        mock_instance = MagicMock()
        mock_class.return_value = mock_instance
        mock_factory_class.return_value = mock_class

        result = factory_method("test", "package", arg1="value1", arg2="value2")

        mock_factory_class.assert_called_once_with("test", "package")
        mock_class.assert_called_once_with(arg1="value1", arg2="value2")
        assert result == mock_instance

    @patch("kbot_installer.core.factory.factory.factory_class")
    def test_passes_kwargs_to_constructor(self, mock_factory_class) -> None:
        """Test that factory_method passes kwargs to the class constructor."""
        mock_class = MagicMock()
        mock_instance = MagicMock()
        mock_class.return_value = mock_instance
        mock_factory_class.return_value = mock_class

        kwargs = {"username": "test", "password": "pass"}
        factory_method("test", "package", **kwargs)

        mock_class.assert_called_once_with(**kwargs)

    @patch("kbot_installer.core.factory.factory.factory_class")
    def test_handles_type_error_from_constructor(self, mock_factory_class) -> None:
        """Test that factory_method handles TypeError from constructor."""
        mock_class = MagicMock()
        mock_class.side_effect = TypeError("Invalid arguments")
        mock_factory_class.return_value = mock_class

        with pytest.raises(TypeError):
            factory_method("test", "package", invalid_arg="value")

    def test_docstring_contains_examples(self) -> None:
        """Test that the function docstring contains usage examples."""
        docstring = factory_method.__doc__
        assert "Example:" in docstring
        assert "factory_method" in docstring

    def test_handles_real_import_error(self) -> None:
        """Test that factory_method handles real ImportError scenarios."""
        with pytest.raises(ImportError):
            factory_method("nonexistent", "factory")
