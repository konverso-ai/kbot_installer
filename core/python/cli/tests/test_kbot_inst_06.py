"""PO sheet KBOT-INST-06 — Admin password: steps used by this sheet only."""

import base64
import re
import string

import pytest
from pytest_bdd import given, scenarios, then

from cli import commands
from cli.tests.bdd.fakes import FakeDatabase
from cli.tests.bdd.steps_common import find_database, names, step
from cli.tests.bdd.environment import Environment
from database.base import DbSettings
from database.utils import SAFE_ENCRYPT_SALT_SIZE, safe_encrypt

scenarios("features/KBOT-INST-06.feature")

HEX_DIGEST_SIZE = 64  # hex digest of HMAC-SHA256


@pytest.fixture
def stored_before() -> dict[str, dict[str, str | None]]:
    """Keep the kbot users of each database (login to password hash) as the Given steps created them."""
    return {}


@pytest.fixture(autouse=True)
def admin_settings(env: Environment) -> list[DbSettings]:
    """Record the database settings the command passes to ``set_admin_password``."""
    calls: list[DbSettings] = []
    original = commands.set_admin_password

    def spy(settings: DbSettings, password: str) -> None:
        """Record the settings, then set the password for real."""
        calls.append(settings)
        original(settings, password)

    env.monkeypatch.setattr(commands, "set_admin_password", spy)
    return calls


@given(step('the database "{db}" contains the kbot users "{users}"'))
def kbot_users(env: Environment, db: str, users: str, stored_before: dict) -> None:
    """Create kbot users, each with a hashed password of its own."""
    database = find_database(env, db)
    for login in names(users):
        database.users[login] = safe_encrypt(f"{login}-old-pwd")
    stored_before[db] = dict(database.users)


@given(step('the internal PostgreSQL server of "{workarea}" holds the database "{db}" and is stopped'))
def internal_server_stopped(env: Environment, workarea: str, db: str) -> None:
    """Create a stopped internal cluster in the workarea, owning a kbot database."""
    env.db.cluster(env.path(workarea) / "var" / "db").server.databases[db] = FakeDatabase(owner="kbot_db_user")


@then(step('the output contains "{prefix}" followed by {count:d} URL-safe characters'))
def output_token(env: Environment, prefix: str, count: int) -> None:
    """Check a line of the output is prefix followed by exactly count URL-safe characters."""
    assert env.result is not None
    pattern = re.escape(prefix) + rf"[A-Za-z0-9_-]{{{count}}}$"
    assert re.search(pattern, env.result.output, re.MULTILINE), env.result.output


@then(step('the password of "{login}" in "{db}" is stored as a salted hash, not as "{password}"'))
def password_hashed(env: Environment, login: str, db: str, password: str) -> None:
    """Check the stored value is base64(hex HMAC-SHA256 digest + '$' + 16-byte salt), never the clear text."""
    stored = find_database(env, db).users.get(login)
    assert stored is not None, f"no password stored for {login!r}"
    assert password not in stored
    raw = base64.b64decode(stored, validate=True)
    digest, dollar = raw[:HEX_DIGEST_SIZE].decode(), raw[HEX_DIGEST_SIZE : HEX_DIGEST_SIZE + 1]
    assert set(digest) <= set(string.hexdigits), raw
    assert dollar == b"$", raw
    assert len(raw) == HEX_DIGEST_SIZE + 1 + SAFE_ENCRYPT_SALT_SIZE, raw


@then(step('the password of "{login}" in "{db}" is unchanged'))
def password_unchanged(env: Environment, login: str, db: str, stored_before: dict) -> None:
    """Check a kbot user still has the password hash it had before the command."""
    assert find_database(env, db).users.get(login) == stored_before[db][login]


@then(step('the kbot users of "{db}" are unchanged'))
def users_unchanged(env: Environment, db: str, stored_before: dict) -> None:
    """Check no kbot user was added, removed or given a new password."""
    assert find_database(env, db).users == stored_before[db]


@then(step('PostgreSQL is located in "{path}"'))
def pg_dir_used(env: Environment, path: str, admin_settings: list[DbSettings]) -> None:
    """Check the command resolved PG_DIR to path (its psql client is path/bin/psql)."""
    assert [env.sanitize(str(s.psql_path)) for s in admin_settings] == [f"{path}/bin/psql"]
