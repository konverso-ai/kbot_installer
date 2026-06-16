"""SSH authentication for Git operations via Dulwich."""

import os
import stat
import tempfile
from collections.abc import Iterator
from pathlib import Path
from types import TracebackType
from typing import Annotated, Self, TypeAlias

import httpx
from pydantic import Field, PrivateAttr, SecretStr, model_validator

from auth.auth_mixin import AuthMixin, RemoteKwargs

GitUsername: TypeAlias = Annotated[str, Field(default="git")]
StrictHostKeyChecking: TypeAlias = Annotated[str, Field(default="accept-new")]

DEFAULT_KEY_FILENAMES: tuple[str, ...] = (
    "id_ed25519",
    "id_rsa",
    "id_ecdsa",
    "id_ecdsa_sk",
    "id_ed25519_sk",
)


class SshAuth(AuthMixin):
    """Authentication for Git over SSH, consumed by Dulwich via ``remote_kwargs``.

    Three mutually exclusive modes:

    * **Local keys** (default): scan ``~/.ssh`` for standard private key filenames.
    * **Agent**: use a forwarded key via ``SSH_AUTH_SOCK`` (``use_agent=True``).
    * **Inline key**: provide ``private_key`` content; use as a context manager so
      the temporary key file is cleaned up after Git operations.

    Dulwich receives ``username``, optional ``key_filename``, and ``ssh_command``.
    """

    username: GitUsername
    strict_host_key_checking: StrictHostKeyChecking
    private_key: SecretStr | None = None
    use_agent: bool = False
    ssh_directory: Path = Field(default_factory=lambda: Path.home() / ".ssh")
    key_filenames: tuple[str, ...] = DEFAULT_KEY_FILENAMES

    _tmpdir: tempfile.TemporaryDirectory[str] | None = PrivateAttr(default=None)
    _key_path: Path | None = PrivateAttr(default=None)

    @model_validator(mode="after")
    def validate_source(self) -> Self:
        if self.private_key is not None and self.use_agent:
            msg = "private_key and use_agent are mutually exclusive"
            raise ValueError(msg)
        return self

    @property
    def key_path(self) -> Path:
        """Resolved private key path, if any (not set in agent mode)."""
        if self.use_agent:
            raise RuntimeError("No SSH private key path is available in agent mode")
        if self._key_path is None:
            self._resolve_key_path()
        return self._key_path

    def auth_flow(self, request: httpx.Request) -> Iterator[httpx.Request]:
        yield request

    def remote_kwargs(self) -> RemoteKwargs:
        kwargs: RemoteKwargs = {
            "username": self.username,
            "ssh_command": self._ssh_command(),
        }
        if self.use_agent:
            if not os.environ.get("SSH_AUTH_SOCK"):
                msg = "SSH_AUTH_SOCK is not set; cannot use forwarded SSH agent"
                raise RuntimeError(msg)
            return kwargs

        kwargs["key_filename"] = str(self._resolve_key_path())
        return kwargs

    def _ssh_command(self) -> str:
        return f"ssh -o StrictHostKeyChecking={self.strict_host_key_checking}"

    def _resolve_key_path(self) -> Path:
        if self._key_path is not None:
            return self._key_path

        if self.private_key is not None:
            self._tmpdir = tempfile.TemporaryDirectory()
            self._key_path = Path(self._tmpdir.name) / "id_ed25519"
            self._key_path.write_text(self.private_key.get_secret_value())
            self._key_path.chmod(stat.S_IRUSR | stat.S_IWUSR)
            return self._key_path

        for name in self.key_filenames:
            candidate = self.ssh_directory / name
            if candidate.is_file():
                self._key_path = candidate
                return candidate

        searched = ", ".join(self.key_filenames)
        msg = f"No SSH private key found in {self.ssh_directory} (tried: {searched})"
        raise FileNotFoundError(msg)

    def __enter__(self) -> "SshAuth":
        if self.private_key is not None:
            self._resolve_key_path()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._tmpdir is not None:
            self._tmpdir.cleanup()
            self._tmpdir = None
            self._key_path = None
