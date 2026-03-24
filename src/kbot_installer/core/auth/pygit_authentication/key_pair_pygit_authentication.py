"""Key pair authentication for PyGit operations.

This module provides authentication using SSH key pairs for git operations.
"""

import pygit2

from kbot_installer.core.auth.pygit_authentication.remote_callback_mixin import (
    RemoteCallbackMixin,
)


class KeyPairPygitAuthentication(RemoteCallbackMixin):
    """Authentication class using SSH key pairs.

    This class provides authentication for git operations using SSH key pairs.
    It implements the PyGitAuthenticationBase interface.

    Attributes:
        username (str): Username for authentication.
        private_key_path (str): Path to the private key file.
        public_key_path (str): Path to the public key file.
        passphrase (str): Passphrase for the private key if encrypted.

    """

    def __init__(
        self,
        username: str,
        private_key_path: str,
        public_key_path: str,
        passphrase: str = "",
    ) -> None:
        """Initialize key pair authentication.

        Args:
            username (str): Username for authentication.
            private_key_path (str): Path to the private key file.
            public_key_path (str): Path to the public key file.
            passphrase (str, optional): Passphrase for the private key if encrypted.
                Defaults to empty string.

        """
        self.username = username
        self.private_key_path = private_key_path
        self.public_key_path = public_key_path
        self.passphrase = passphrase

    def _get_credentials(self) -> pygit2.Keypair:
        """Get SSH key pair credentials for authentication.

        Returns:
            pygit2.Keypair: SSH key pair credentials for authentication.

        """
        return pygit2.Keypair(
            self.username, self.public_key_path, self.private_key_path, self.passphrase
        )
