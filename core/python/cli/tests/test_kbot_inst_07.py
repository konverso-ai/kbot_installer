"""PO sheet KBOT-INST-07 — Uninstallation: steps used by this sheet only."""

from datetime import datetime

from pytest_bdd import given, scenarios, then

from cli.tests.bdd.fakes import FakeDatabase
from cli.tests.bdd.steps_common import find_database, step
from cli.tests.bdd.environment import Environment

scenarios("features/KBOT-INST-07.feature")


# Given


@given(step('the internal database of "{directory}" holds the database "{db}" owned by "{user}" with the password "{password}"'))
def internal_database(env: Environment, directory: str, db: str, user: str, password: str) -> None:
    """Create a login role and a database it owns in the internal cluster of a workarea."""
    server = env.db.cluster(env.path(directory) / "var" / "db").server
    server.roles[user] = password
    server.databases[db] = FakeDatabase(owner=user)


@given(step('the internal PostgreSQL server of "{directory}" is running on port {port:d}'))
def internal_server_started(env: Environment, directory: str, port: int) -> None:
    """Start the internal cluster of a workarea on a port."""
    env.db.cluster(env.path(directory) / "var" / "db").port = port


@given(step('the internal PostgreSQL server of "{directory}" is stopped'))
def internal_server_stopped(env: Environment, directory: str) -> None:
    """Leave the internal cluster of a workarea stopped."""
    env.db.cluster(env.path(directory) / "var" / "db").port = None


@given(step('the internal PostgreSQL server of "{directory}" keeps running after "pg_ctl stop"'))
def internal_server_unstoppable(env: Environment, directory: str) -> None:
    """Make 'pg_ctl stop' on the cluster of a workarea return without stopping the server."""
    env.procs.on(f"pg_ctl -D {directory}/var/db --silent stop")


@given(step('the local date and time is "{timestamp}"'))
def local_time(env: Environment, timestamp: str) -> None:
    """Freeze the clock the installer names its timestamped files with."""
    frozen = datetime.fromisoformat(timestamp)

    class FrozenDatetime(datetime):
        """datetime whose now() is the frozen local time."""

        @classmethod
        def now(cls, tz: object = None) -> datetime:  # noqa: ARG003 - same signature as datetime.now
            """Return the frozen local time."""
            return frozen

    env.monkeypatch.setattr("cli.commands.datetime", FrozenDatetime)


@given(step('the program "{program}" fails with "{message}"'))
def program_fails(env: Environment, program: str, message: str) -> None:
    """Make a program (basename, optionally with its first arguments) exit with code 1 and print message on stderr."""
    env.procs.on(program, 1, stderr=message)


@given(step('the database server "{host}" port {port:d} is unreachable'))
def server_unreachable(env: Environment, host: str, port: int) -> None:
    """Make sure nothing answers on host:port."""
    env.db.servers.pop((host, port), None)


# Then


@then(step('the objects owned by "{user}" in "{db}" are dropped'))
def owned_objects_dropped(env: Environment, user: str, db: str) -> None:
    """Check 'DROP OWNED BY CURRENT_USER' ran in db on a connection as user, leaving no table."""
    assert any(c[2] == db and c[3] == user for c in env.db.connections), env.db.connections
    assert (db, "DROP OWNED BY CURRENT_USER") in env.db.executed, env.db.executed
    assert find_database(env, db).tables == set()
