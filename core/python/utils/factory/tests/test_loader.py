"""Tests for factory module."""

from unittest.mock import MagicMock, patch

import pytest

from utils.factory.loader import (
    factory_class,
    factory_function,
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
            factory_class("nonexistent_class", "utils.factory")

    def test_handles_real_import_error(self) -> None:
        """Test that factory_class handles real ImportError scenarios."""
        with pytest.raises(ImportError):
            factory_class("nonexistent", "utils.factory")

    @patch("importlib.import_module")
    @patch(
        "utils.factory.loader.build_class_name",
        return_value="UtilsFactory",
    )
    @patch(
        "utils.factory.loader.build_module_name", return_value="utils"
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


class TestFactoryFunction:
    """Test cases for factory_function function."""

    def test_function_exists(self) -> None:
        """Test that factory_function function exists and is callable."""
        assert callable(factory_function)

    def test_returns_class_from_explicit_module(self) -> None:
        """Test that factory_function returns a class using explicit module/attribute names."""
        result = factory_function("utils.factory.loader", "factory_class")
        assert result is factory_class

    def test_returns_arbitrary_attribute(self) -> None:
        """Test that factory_function can retrieve non-class attributes too."""
        result = factory_function("utils.factory.loader", "T")
        from utils.factory.loader import T as expected_type_var

        assert result is expected_type_var

    def test_handles_import_error(self) -> None:
        """Test that factory_function raises ImportError for a missing module."""
        with pytest.raises(ImportError):
            factory_function("nonexistent.module.path", "SomeClass")

    def test_handles_attribute_error(self) -> None:
        """Test that factory_function raises AttributeError for a missing attribute."""
        with pytest.raises(AttributeError):
            factory_function("utils.factory.loader", "NonExistentAttribute")

    @patch("importlib.import_module")
    def test_uses_import_module_and_getattr_directly(self, mock_import_module) -> None:
        """Test that factory_function does not build module/class names."""
        mock_module = MagicMock()
        mock_attribute = MagicMock()
        mock_module.CustomAttribute = mock_attribute
        mock_import_module.return_value = mock_module

        result = factory_function("some.explicit.module", "CustomAttribute")

        mock_import_module.assert_called_once_with("some.explicit.module")
        assert result == mock_attribute

    def test_does_not_require_naming_convention(self) -> None:
        """Test that module and attribute names may differ from the factory_class convention."""
        # "utils" module, "build_class_name" attribute: no {name}_{package} relationship.
        result = factory_function("utils.factory.utils", "build_class_name")
        from utils.factory.utils import build_class_name as expected

        assert result is expected


class TestFactoryObject:
    """Test cases for factory_object function."""

    @patch("utils.factory.loader.factory_function")
    def test_calls_factory_function_and_instantiates(self, mock_factory_function) -> None:
        """Test that factory_object calls factory_function and instantiates the class."""
        mock_class = MagicMock()
        mock_instance = MagicMock()
        mock_class.return_value = mock_instance
        mock_factory_function.return_value = mock_class

        result = factory_object("test", "package", arg1="value1", arg2="value2")

        mock_factory_function.assert_called_once_with("package.test_package", "TestPackage")
        mock_class.assert_called_once_with(arg1="value1", arg2="value2")
        assert result == mock_instance

    @patch("utils.factory.loader.factory_function")
    def test_passes_kwargs_to_constructor(self, mock_factory_function) -> None:
        """Test that factory_object passes kwargs to the class constructor."""
        mock_class = MagicMock()
        mock_instance = MagicMock()
        mock_class.return_value = mock_instance
        mock_factory_function.return_value = mock_class

        kwargs = {"username": "test", "password": "pass"}
        factory_object("test", "package", **kwargs)

        mock_class.assert_called_once_with(**kwargs)

    @patch("utils.factory.loader.factory_function")
    def test_handles_type_error_from_constructor(self, mock_factory_function) -> None:
        """Test that factory_object handles TypeError from constructor."""
        mock_class = MagicMock()
        mock_class.side_effect = TypeError("Invalid arguments")
        mock_factory_function.return_value = mock_class

        with pytest.raises(TypeError):
            factory_object("test", "package", invalid_arg="value")

    def test_handles_real_import_error(self) -> None:
        """Test that factory_object handles real ImportError scenarios."""
        with pytest.raises(ImportError):
            factory_object("nonexistent", "utils.factory")


class TestFactoryMethod:
    """Test cases for factory_method function."""

    @patch("utils.factory.loader.factory_object")
    def test_delegates_to_factory_object(self, mock_factory_object) -> None:
        """Test that factory_method delegates to factory_object."""
        mock_instance = MagicMock()
        mock_factory_object.return_value = mock_instance

        result = factory_method("test", "package", arg1="value1", arg2="value2")

        mock_factory_object.assert_called_once_with(
            "test", "package", arg1="value1", arg2="value2"
        )
        assert result == mock_instance

    @patch("utils.factory.loader.factory_object")
    def test_passes_kwargs_through(self, mock_factory_object) -> None:
        """Test that factory_method passes kwargs through to factory_object."""
        kwargs = {"username": "test", "password": "pass"}
        factory_method("test", "package", **kwargs)

        mock_factory_object.assert_called_once_with("test", "package", **kwargs)

    @patch("utils.factory.loader.factory_object")
    def test_propagates_type_error(self, mock_factory_object) -> None:
        """Test that factory_method propagates TypeError raised by factory_object."""
        mock_factory_object.side_effect = TypeError("Invalid arguments")

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
            factory_method("nonexistent", "utils.factory")
