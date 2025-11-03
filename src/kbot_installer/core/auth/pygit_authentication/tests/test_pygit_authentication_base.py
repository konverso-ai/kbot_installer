"""Tests for pygit_authentication_base module."""

from abc import ABC

import pytest

from kbot_installer.core.auth.pygit_authentication.pygit_authentication_base import (
    PyGitAuthenticationBase,
)


class TestPyGitAuthenticationBase:
    """Test cases for PyGitAuthenticationBase class."""

    def test_is_abstract_base_class(self) -> None:
        """Test that PyGitAuthenticationBase is an abstract base class."""
        assert issubclass(PyGitAuthenticationBase, ABC)

    def test_abstract_methods_exist(self) -> None:
        """Test that abstract methods are defined."""
        abstract_methods = PyGitAuthenticationBase.__abstractmethods__
        assert "_get_credentials" in abstract_methods
        assert "get_connector" in abstract_methods

    def test_cannot_instantiate_directly(self) -> None:
        """Test that PyGitAuthenticationBase cannot be instantiated directly."""
        with pytest.raises(TypeError):
            PyGitAuthenticationBase()

    def test_abstract_methods_signature(self) -> None:
        """Test that abstract methods have correct signatures."""
        # Check _get_credentials method signature
        credentials_method = PyGitAuthenticationBase._get_credentials
        assert callable(credentials_method)

        # Check get_connector method signature
        connector_method = PyGitAuthenticationBase.get_connector
        assert callable(connector_method)
