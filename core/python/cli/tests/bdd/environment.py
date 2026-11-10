"""Scenario state: a sandboxed filesystem, environment and fakes, and the CLI runner."""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from click.testing import CliRunner
from dulwich import porcelain

import cli.__main__
from cli import commands
from cli.tests.bdd.fakes import FakeGitRemotes, FakeProcesses, FakeStorage

# Console scripts of pyproject.toml [project.scripts]; kbot-installer goes through main() for its error handling.
CONSOLE_SCRIPTS: dict[str, Callable[[], object]] = {
    "kbot-installer": cli.__main__.main,
    "kbot-load": lambda: commands.load(standalone_mode=True),
    "kbot-learn": lambda: commands.learn(standalone_mode=True),
    "kbot-set-admin-password": lambda: commands.set_admin_password_command(standalone_mode=True),
}

# Variables a developer's shell may hold that would change what a scenario exercises.
CLEARED_ENV = ("KBOT_ADMIN_PASSWORD", "PG_DIR", "PG_ADMIN_PASSWORD", "KBOT_INSTALLER", "LD_LIBRARY_PATH")


@dataclass
class Result:
    """What a command printed and how it exited."""

    exit_code: int
    stdout: str
    stderr: str
    output: str


@dataclass
class Environment:
    """Everything a scenario sets up, runs and asserts on; absolute step paths live under ``root``."""

    root: Path
    monkeypatch: pytest.MonkeyPatch
    answers: list[str] = field(default_factory=list)
    result: Result | None = None
    procs: FakeProcesses = field(init=False)
    storage: FakeStorage = field(default_factory=FakeStorage)
    git: FakeGitRemotes = field(init=False)

    def __post_init__(self) -> None:
        """Create the fakes that need the sandbox."""
        self.procs = FakeProcesses(sanitize=self.sanitize)
        self.git = FakeGitRemotes(self.root)

    def path(self, p: str) -> Path:
        """Map an absolute path written in a step into the sandbox."""
        return self.root / p.lstrip("/")

    def sanitize(self, text: str) -> str:
        """Strip the sandbox prefix so assertions read the paths written in the steps."""
        return text.replace(str(self.root), "")

    def setenv(self, name: str, value: str | None) -> None:
        """Set (or delete, for None) an environment variable for the rest of the scenario."""
        if value is None:
            self.monkeypatch.delenv(name, raising=False)
        else:
            self.monkeypatch.setenv(name, value)

    def interrupt(self) -> None:
        """Make the next call to any fake raise KeyboardInterrupt, as Ctrl-C would."""
        self.procs.interrupt = self.storage.interrupt = self.git.interrupt = True

    def run(self, cmdline: str) -> Result:
        """Run a console script as the operator would, capturing its output and exit code."""
        argv = [str(self.path(arg)) if arg.startswith("/") else arg for arg in shlex.split(cmdline)]
        entry = CONSOLE_SCRIPTS[argv[0]]
        self.monkeypatch.setattr(sys, "argv", argv)
        stdin = "".join(f"{answer}\n" for answer in self.answers)
        exit_code = 0
        with CliRunner().isolation(input=stdin) as (stdout, stderr, output):
            try:
                entry()
            except SystemExit as e:
                exit_code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
            self.result = Result(
                exit_code,
                *(self.sanitize(s.getvalue().decode()) for s in (stdout, stderr, output)),
            )
        return self.result


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Environment:
    """Provide a fresh sandboxed env, with every external system replaced by a fake."""
    w = Environment(root=tmp_path, monkeypatch=monkeypatch)
    home = w.path("/home/kbot")
    home.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("COLUMNS", "200")
    for name in [*CLEARED_ENV, *(n for n in os.environ if n.startswith("NEXUS_"))]:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(subprocess, "run", w.procs.run)
    monkeypatch.setattr(subprocess, "Popen", w.procs.popen)
    monkeypatch.setattr(
        "git.provider.factory.add_storage_from_config",
        lambda _config, backend, area=None, auth=None: w.storage.area(backend, area),  # noqa: ARG005
    )
    original_transport = porcelain.get_transport_and_path
    monkeypatch.setattr(
        porcelain,
        "get_transport_and_path",
        lambda location, *a, **kw: original_transport(w.git.rewrite(location), *a, **kw),
    )
    # Under "python -m pytest", click would name the program after pytest instead of the console script.
    monkeypatch.setattr("click.core._detect_program_name", lambda *_a, **_kw: Path(sys.argv[0]).name)
    return w
