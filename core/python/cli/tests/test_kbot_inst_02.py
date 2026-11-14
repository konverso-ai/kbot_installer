"""PO sheet KBOT-INST-02 — Installation: steps used by this sheet only."""

import re
import shutil

from pytest_bdd import scenarios, then

from cli.tests.bdd.steps_common import find_database, step, table_rows
from cli.tests.bdd.environment import Environment
from database.utils import safe_encrypt

scenarios("features/KBOT-INST-02.feature")


def printed_after(env: Environment, prefix: str) -> str:
    """Return the value the last command printed after prefix, up to the end of the line."""
    assert env.result is not None
    match = re.search(re.escape(prefix) + r"(\S+)", env.result.output)
    assert match, f"{prefix!r} not printed:\n{env.result.output}"
    return match.group(1)


@then(step('the password of "{login}" in "{db}" verifies the password printed after "{prefix}"'))
def password_verifies_printed(env: Environment, login: str, db: str, prefix: str) -> None:
    """Check the stored kbot password hash matches the generated password the command printed."""
    stored = find_database(env, db).users.get(login)
    assert stored is not None, f"no password stored for {login!r}"
    assert safe_encrypt(printed_after(env, prefix), stored) == stored


@then(step('the user "{user}" on "{host}" port {port:d} has the password printed after "{prefix}"'))
def role_password_printed(env: Environment, user: str, host: str, port: int, prefix: str) -> None:
    """Check a PostgreSQL login role got the generated password the command printed."""
    server = env.db.server(host, port)
    assert server is not None, f"no server on {host}:{port}"
    assert server.roles.get(user) == printed_after(env, prefix)


@then(step('the database server "{host}" port {port:d} was contacted as "{user}" with the password "{password}"'))
def contacted_as(env: Environment, host: str, port: int, user: str, password: str) -> None:
    """Check a connection was opened to a server with these credentials."""
    assert any(c[0] == host and c[1] == port and c[3:] == (user, password) for c in env.db.connections)


@then(step('the internal PostgreSQL server of "{workarea}" is running on port {port:d}'))
def internal_server_running(env: Environment, workarea: str, port: int) -> None:
    """Check the cluster of a workarea is still running when the command ends."""
    assert env.db.cluster(env.path(workarea) / "var" / "db").port == port


@then(step('no role and no database is created on "{host}"'))
def nothing_created(env: Environment, host: str) -> None:
    """Check the installer created no PostgreSQL role nor database (on any server, the internal one included)."""
    assert not [s for _, s in env.db.executed if s.startswith(("CREATE ROLE", "CREATE DATABASE"))], host
    assert not env.db.clusters


@then(step('the database "{db}" has the table "{table}"'))
def has_table(env: Environment, db: str, table: str) -> None:
    """Check a table exists in the public schema of a database."""
    assert table in find_database(env, db).tables


@then(step('the database "{db}" records no schema version'))
def no_schema_version(env: Environment, db: str) -> None:
    """Check the __schema_version table holds no row."""
    assert find_database(env, db).versions == set()


@then(step('the password of "{login}" in "{db}" is set before "{command}" runs'))
def password_set_before(env: Environment, login: str, db: str, command: str) -> None:
    """Check the kbot password update happened before a process ran."""
    updates = [i for i, e in enumerate(env.events) if e.startswith(f"sql {db}: UPDATE users_im_account")]
    runs = [i for i, e in enumerate(env.events) if e.startswith(f"run {command}")]
    assert updates, f"the password of {login!r} was never set"
    assert runs, f"{command!r} never ran"
    assert updates[0] < runs[0], env.events


@then(step('the output, apart from the download table, is the same as for "{cmdline}" on a fresh workarea'))
def same_output_apart_from_table(env: Environment, cmdline: str) -> None:
    """Rerun without -V on a deleted workarea and database (install refuses an existing one), compare the other lines."""
    assert env.result is not None

    def other_lines() -> list[str]:
        """Return the output lines that are not download table rows."""
        rows = [" ".join(r) for r in table_rows(env) if len(r) >= 3]  # noqa: PLR2004 - product, provider, status
        lines = [" ".join(re.split(r"\s{2,}", s.strip())) for s in re.split(r"[\r\n]", env.result.output)]
        return [line for line in lines if line and line not in rows and "In progress" not in line]

    verbose = other_lines()
    workarea = env.path("/home/kbot/dev/work")
    shutil.rmtree(workarea)
    env.db.clusters = {d: c for d, c in env.db.clusters.items() if not d.is_relative_to(workarea)}
    env.run(cmdline)
    assert other_lines() == verbose
