"""Tests for git.versioner.unsupported_ops_mixin module."""

from pathlib import Path

import pytest

from git.versioner.base import VersionerError
from git.versioner.unsupported_ops_mixin import UnsupportedOpsMixin
from utils.utils_for_unit_tests import compare


class _StubVersioner(UnsupportedOpsMixin):
    """Minimal versioner implementing only supported operations."""

    name = "stub"
    base_url = ""

    def _get_auth(self) -> None:
        return None

    def remote_exists(self, repository_url: str) -> bool:
        return False

    def clone(
        self,
        repository_url: str,
        target_path: str | Path,
        *,
        branch: str | None = None,
        depth: int | None = None,
    ) -> None:
        return None

    def list_remote_branches(self, repository_url: str) -> list[str]:
        return []

    def pull(self, repository_path: str | Path, branch: str) -> None:
        return None


@pytest.mark.parametrize(
    "method_name, expected_message",
    [
        ("add", UnsupportedOpsMixin.git_ops_unsupported),
        ("fetch", UnsupportedOpsMixin.git_ops_unsupported),
        ("commit", UnsupportedOpsMixin.git_ops_unsupported),
        ("push", UnsupportedOpsMixin.git_ops_unsupported),
        ("push_branches", UnsupportedOpsMixin.git_ops_unsupported),
        ("checkout", UnsupportedOpsMixin.checkout_unsupported),
        ("select_branch", UnsupportedOpsMixin.select_branch_unsupported),
        ("stash", UnsupportedOpsMixin.stash_unsupported),
        ("safe_pull", UnsupportedOpsMixin.safe_pull_unsupported),
    ],
)
def test_unsupportedopsmixin_invalid_raises_versioner_error(
    method_name: str,
    expected_message: str,
) -> None:
    versioner = _StubVersioner()
    method = getattr(versioner, method_name)
    with pytest.raises(VersionerError) as exc_info:
        if method_name == "commit":
            method(Path("/repo"), "message")
        elif method_name == "stash":
            method(Path("/repo"))
        elif method_name == "push_branches":
            method(Path("/repo"), ["main"])
        elif method_name == "select_branch":
            method(Path("/repo"), ["main"])
        elif method_name in {"push", "checkout", "safe_pull"}:
            method(Path("/repo"), "main")
        else:
            method(Path("/repo"))
    assert compare("eq", str(exc_info.value), expected_message)
