"""Tests for versioner.base module."""

from abc import ABC

import pytest

from git.versioner.base import VersionerBase


class TestVersionerBase:
    """Test cases for VersionerBase."""

    def test_is_abstract_base_class(self) -> None:
        """Test that VersionerBase is an abstract base class."""
        assert issubclass(VersionerBase, ABC)

    def test_abstract_methods_exist(self) -> None:
        """Test that abstract methods are defined."""
        abstract_methods = VersionerBase.__abstractmethods__
        assert "_get_auth" in abstract_methods
        assert "clone" in abstract_methods

    def test_cannot_instantiate_directly(self) -> None:
        """Test that VersionerBase cannot be instantiated directly."""
        with pytest.raises(TypeError):
            VersionerBase()

    def test_abstract_methods_are_callable(self) -> None:
        """Test that abstract methods are callable."""
        # Check _get_auth method signature
        get_auth_method = VersionerBase._get_auth
        assert callable(get_auth_method)

        # Check clone method signature
        clone_method = VersionerBase.clone
        assert callable(clone_method)
