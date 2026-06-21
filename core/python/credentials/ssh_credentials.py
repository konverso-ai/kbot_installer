"""SSH credentials based on local keys or a forwarded agent."""

import os
from pathlib import Path

from auth.ssh_auth import DEFAULT_KEY_FILENAMES


class SshCredentials:
    """Credentials satisfied by a local SSH key or ``SSH_AUTH_SOCK``."""

    def missing_env_vars(self) -> list[str]:
        """Return a descriptive message when no SSH authentication source is available."""
        if os.environ.get("SSH_AUTH_SOCK"):
            return []

        ssh_dir = Path.home() / ".ssh"
        if any((ssh_dir / name).is_file() for name in DEFAULT_KEY_FILENAMES):
            return []

        return [
            "SSH private key in ~/.ssh (id_ed25519, id_rsa, ...) or SSH_AUTH_SOCK",
        ]

    def auth_kwargs(self) -> dict[str, str] | None:
        if self.missing_env_vars():
            return None
        return {"username": "git"}
