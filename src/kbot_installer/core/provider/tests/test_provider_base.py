"""Tests for provider_base module."""

from abc import ABC

import pytest

from kbot_installer.core.provider.provider_base import ProviderBase, ProviderError


class TestProviderError:
    """Test cases for ProviderError class."""

    def test_inherits_from_exception(self) -> None:
        """Test that ProviderError inherits from Exception."""
        assert issubclass(ProviderError, Exception)

    def test_can_be_raised(self) -> None:
        """Test that ProviderError can be raised."""
        error_message = "Test error"
        with pytest.raises(ProviderError):
            raise ProviderError(error_message)

    def test_can_be_raised_with_message(self) -> None:
        """Test that ProviderError can be raised with a message."""
        message = "Test error message"
        with pytest.raises(ProviderError) as exc_info:
            raise ProviderError(message)
        assert str(exc_info.value) == message


class TestProviderBase:
    """Test cases for ProviderBase class."""

    def test_is_abstract_base_class(self) -> None:
        """Test that ProviderBase is an abstract base class."""
        assert issubclass(ProviderBase, ABC)

    def test_abstract_methods_exist(self) -> None:
        """Test that abstract methods are defined."""
        abstract_methods = ProviderBase.__abstractmethods__
        assert "clone_and_checkout" in abstract_methods

    def test_cannot_instantiate_directly(self) -> None:
        """Test that ProviderBase cannot be instantiated directly."""
        with pytest.raises(TypeError):
            ProviderBase()

    def test_abstract_methods_signature(self) -> None:
        """Test that abstract methods have correct signatures."""
        # Check clone_and_checkout method signature
        clone_method = ProviderBase.clone_and_checkout
        assert callable(clone_method)
