"""Base class for PyGit authentication.

This module defines the abstract base class that all PyGit authentication
classes must implement to provide a unified interface for git operations.
"""

from abc import ABC, abstractmethod

import pygit2


class PyGitAuthenticationBase(ABC):
    """Abstract base class for PyGit authentication.

    This class defines the interface that all PyGit authentication classes must implement.
    It provides methods for getting credentials and remote callbacks for git operations.

    """

    @abstractmethod
    def _get_credentials(self) -> pygit2.Keypair | pygit2.UserPass:
        """Get the credentials for authentication.

        Returns:
            pygit2.Keypair | pygit2.UserPass: The credentials object for authentication.

        """

    @abstractmethod
    def get_connector(self) -> pygit2.RemoteCallbacks:
        """Get a remote callbacks object for git operations.

        Returns:
            pygit2.RemoteCallbacks: A remote callbacks object that can be used with PyGit
                for authentication during git operations.

        """
