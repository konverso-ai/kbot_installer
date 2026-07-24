"""SSH credentials for GitHub, based on local keys or a forwarded agent."""

from credentials.ssh_utils import ssh_auth_kwargs, ssh_missing_env_vars


class SshGithubCredentials:
    """GitHub credentials satisfied by a local SSH key or ``SSH_AUTH_SOCK``."""

    def missing_env_vars(self) -> list[str]:
        """Return a descriptive message when no SSH authentication source is available.

        Returns:
            An empty list when a local key or forwarded agent is available,
            otherwise a single-item list describing the missing source.

        """
        return ssh_missing_env_vars()

    def auth_kwargs(self) -> dict[str, object]:
        """Return keyword arguments for ``add_ssh_auth("ssh", **kwargs)``."""
        return ssh_auth_kwargs()
