"""Tests for http_auth_base module."""

from abc import ABC

import pytest

from kbot_installer.core.auth.http_auth.http_auth_base import HttpAuthBase


class TestHttpAuthBase:
    """Test cases for HttpAuthBase class."""

    def test_is_abstract_base_class(self) -> None:
        """Test that HttpAuthBase is an abstract base class."""
        assert issubclass(HttpAuthBase, ABC)

    def test_abstract_methods_exist(self) -> None:
        """Test that abstract methods are defined."""
        abstract_methods = HttpAuthBase.__abstractmethods__
        assert "get_auth" in abstract_methods

    def test_cannot_instantiate_directly(self) -> None:
        """Test that HttpAuthBase cannot be instantiated directly."""
        with pytest.raises(TypeError):
            HttpAuthBase()

    def test_get_auth_method_signature(self) -> None:
        """Test that get_auth method has correct signature."""
        get_auth_method = HttpAuthBase.get_auth
        assert callable(get_auth_method)
