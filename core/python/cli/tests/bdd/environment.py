"""Scenario state: a sandboxed filesystem, environment and fakes, and the CLI runner."""

from __future__ import annotations

import logging
import os
import shlex
import subprocess
import sys
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path

import psycopg
import pytest
from click.testing import CliRunner
from dulwich import porcelain

import cli.__main__
from cli import commands
from cli.tests.bdd.fakes import FakeDb, FakeGitRemotes, FakeProcesses, FakeStorage

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
    events: list[str] = field(default_factory=list)
    logs: list[logging.LogRecord] = field(default_factory=list)
    procs: FakeProcesses = field(init=False)
    storage: FakeStorage = field(default_factory=FakeStorage)
    git: FakeGitRemotes = field(init=False)
    db: FakeDb = field(init=False)

    def __post_init__(self) -> None:
        """Create the fakes that need the sandbox, sharing one event log."""
        self.procs = FakeProcesses(sanitize=self.sanitize, events=self.events)
        self.git = FakeGitRemotes(self.root)
        self.db = FakeDb(events=self.events, sanitize=self.sanitize)
        for match in ("python.sh -m utils.License", "pip3.sh install"):
            self.procs.on(match)
        for match, handler in (
            ("pg_ctl", self.db.pg_ctl),
            ("psql", self.db.psql),
            ("pg_dump", self.db.pg_dump),
            ("core.sh load", self.db.load),
            ("kbot.sh load", self.db.load),
        ):
            self.procs.on(match, handler=handler)

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
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Environment]:
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
    monkeypatch.setattr(psycopg, "connect", w.db.connect)
    monkeypatch.setattr("database.postgres_cluster._port_in_use", lambda _host, port: port in w.db.ports_in_use)
    monkeypatch.setattr("database.postgres_cluster._find_port_owner_pid", w.db.ports_in_use.get)
    # Under "python -m pytest", click would name the program after pytest instead of the console script.
    monkeypatch.setattr("click.core._detect_program_name", lambda *_a, **_kw: Path(sys.argv[0]).name)
    handler = _ListHandler(w.logs)
    loggers = [logging.getLogger(), logging.getLogger("kbot")]  # the "kbot" logger does not propagate
    for logger in loggers:
        logger.addHandler(handler)
    yield w
    for logger in loggers:
        logger.removeHandler(handler)


class _ListHandler(logging.Handler):
    """Keep the log records of a scenario, for the steps that check what was logged."""

    def __init__(self, records: list[logging.LogRecord]) -> None:
        """Collect into records."""
        super().__init__(logging.DEBUG)
        self.records = records

    def emit(self, record: logging.LogRecord) -> None:
        """Keep the record."""
        self.records.append(record)
