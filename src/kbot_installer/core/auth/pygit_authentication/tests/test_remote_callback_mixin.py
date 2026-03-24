"""Tests for remote_callback_mixin module."""

import pygit2
import pytest

from kbot_installer.core.auth.pygit_authentication.pygit_authentication_base import (
    PyGitAuthenticationBase,
)
from kbot_installer.core.auth.pygit_authentication.remote_callback_mixin import (
    RemoteCallbackMixin,
)


class ConcreteAuth(RemoteCallbackMixin):
    """Concrete implementation for testing."""

    def _get_credentials(self):
        """Return test credentials."""
        return pygit2.UserPass("test_user", "test_pass")


class TestRemoteCallbackMixin:
    """Test cases for RemoteCallbackMixin class."""

    def test_inherits_from_pygit_authentication_base(self) -> None:
        """Test that RemoteCallbackMixin inherits from PyGitAuthenticationBase."""
        assert issubclass(RemoteCallbackMixin, PyGitAuthenticationBase)

    def test_can_be_instantiated_with_concrete_implementation(self) -> None:
        """Test that RemoteCallbackMixin can be instantiated with concrete implementation."""
        auth = ConcreteAuth()
        assert isinstance(auth, RemoteCallbackMixin)
        assert isinstance(auth, PyGitAuthenticationBase)

    def test_get_connector_returns_remote_callbacks(self) -> None:
        """Test that get_connector returns a RemoteCallbacks object."""
        auth = ConcreteAuth()
        callbacks = auth.get_connector()

        assert isinstance(callbacks, pygit2.RemoteCallbacks)
        assert callbacks.credentials is not None

    def test_get_connector_uses_credentials_from_get_credentials(self) -> None:
        """Test that get_connector uses credentials from _get_credentials method."""
        auth = ConcreteAuth()
        callbacks = auth.get_connector()

        # Verify that the credentials are properly set
        assert callbacks.credentials is not None
        assert isinstance(callbacks.credentials, pygit2.UserPass)

    def test_cannot_instantiate_directly(self) -> None:
        """Test that RemoteCallbackMixin cannot be instantiated directly."""
        with pytest.raises(TypeError):
            RemoteCallbackMixin()
