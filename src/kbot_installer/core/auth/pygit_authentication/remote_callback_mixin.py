"""Mixin for PyGit remote callbacks.

This module provides a mixin class that handles the creation of RemoteCallbacks
objects for PyGit authentication classes.
"""

import pygit2

from kbot_installer.core.auth.pygit_authentication.pygit_authentication_base import (
    PyGitAuthenticationBase,
)


class RemoteCallbackMixin(PyGitAuthenticationBase):
    """Mixin class for creating RemoteCallbacks objects.

    This mixin provides a common implementation for creating pygit2.RemoteCallbacks
    objects with credentials. Classes that inherit from this mixin must implement
    the _get_credentials method to provide the specific credentials.

    """

    def get_connector(self) -> pygit2.RemoteCallbacks:
        """Get a remote callbacks object for git operations.

        This method creates a RemoteCallbacks object using the credentials
        provided by the _get_credentials method.

        Returns:
            pygit2.RemoteCallbacks: A remote callbacks object that can be used with PyGit
                for authentication during git operations.

        """
        credentials = self._get_credentials()
        return pygit2.RemoteCallbacks(credentials=credentials)
