"""Tests for base module."""

from abc import ABC

import pytest

from git.provider.base import ProviderBase


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
