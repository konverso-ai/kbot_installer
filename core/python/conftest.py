"""Session-wide pytest fixtures shared by every test package under ``core/python``."""

import os
from collections.abc import Iterator

import pytest


@pytest.fixture(autouse=True, scope="session")
def _fast_isolated_git() -> Iterator[None]:
    """Make git-backed tests fast and independent of the developer's git setup.

    - ``os.fsync`` is a no-op: dulwich fsyncs every ref/index/config write, which costs
      ~13 ms per call on network-backed disks and is useless for throwaway test repos.
    - ``GIT_CONFIG_GLOBAL``/``GIT_CONFIG_NOSYSTEM`` stop dulwich and the git CLI from
      reading ``~/.gitconfig`` and ``/etc/gitconfig``, which dulwich re-parses on every
      repository open and which would otherwise leak user settings into test outcomes.

    Yields:
        None, once the patches are in place for the whole session.

    """
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(os, "fsync", lambda _fd: None)
        mp.setenv("GIT_CONFIG_GLOBAL", os.devnull)
        mp.setenv("GIT_CONFIG_NOSYSTEM", "1")
        yield
