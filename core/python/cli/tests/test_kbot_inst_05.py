"""PO sheet KBOT-INST-05 — Database objects loading and training: steps used by this sheet only."""

import errno
import os
import subprocess
import sys

import pytest
from pytest_bdd import given, scenarios, then

from cli.tests.bdd.steps_common import step
from cli.tests.bdd.environment import Environment

scenarios("features/KBOT-INST-05.feature")


@pytest.fixture(autouse=True)
def workarea_scripts(env: Environment) -> None:
    """Run processes like the OS does: a missing program raises, and output not captured reaches the terminal."""

    def run(args: list[str], *a: object, **kw: object) -> subprocess.CompletedProcess[str | bytes]:
        """Stand in for ``subprocess.run`` on top of the shared process fake."""
        if not os.path.exists(args[0]):  # noqa: PTH110 - same check as the exec the real call does
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), str(args[0]))
        result = env.procs.run(args, *a, **kw)
        if not kw.get("capture_output") and kw.get("stdout") is None:
            out = result.stdout
            sys.stdout.write(out.decode() if isinstance(out, bytes) else out)
        return result

    env.monkeypatch.setattr(subprocess, "run", run)


@given(step('the program "{program}" prints "{text}"'))
def program_prints(env: Environment, program: str, text: str) -> None:
    """Make a program (basename, optionally with its first arguments) print a line on its standard output."""
    env.procs.on(program, stdout=f"{text}\n")


@then(step('the only command run is "{argv}"'))
def only_command_run(env: Environment, argv: str) -> None:
    """Check exactly one process ran, with exactly this command line."""
    assert env.procs.calls == [argv.split()], env.procs.calls
