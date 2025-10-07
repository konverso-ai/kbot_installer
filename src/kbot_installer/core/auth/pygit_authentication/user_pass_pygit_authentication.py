"""Username/password authentication for PyGit operations.

This module provides authentication using username and password for git operations.
"""

import pygit2

from kbot_installer.core.auth.pygit_authentication.remote_callback_mixin import (
    RemoteCallbackMixin,
)


class UserPassPygitAuthentication(RemoteCallbackMixin):
    """Authentication class using username and password.

    This class provides authentication for git operations using username and password.
    It implements the PyGitAuthenticationBase interface.

    Attributes:
        username (str): Username for authentication.
        password (str): Password for authentication.

    """

    def __init__(self, username: str, password: str) -> None:
        """Initialize username/password authentication.

        Args:
            username (str): Username for authentication.
            password (str): Password for authentication.

        """
        self.username = username
        self.password = password

    def _get_credentials(self) -> pygit2.UserPass:
        """Get username/password credentials for authentication.

        Returns:
            pygit2.UserPass: Username/password credentials for authentication.

        """
        return pygit2.UserPass(self.username, self.password)
