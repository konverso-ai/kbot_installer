"""Step vocabulary shared by the KBOT-INST-0N feature files.

Quoted step values never contain a double quote, which keeps steps that only differ
by a suffix (``... of branch "dev"`` / ``... of branch "dev" with parents "kbot"``) apart.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from dulwich import porcelain
from dulwich.repo import Repo
from pytest_bdd import given, parsers, then, when

from cli.tests.bdd.fakes import FakeDatabase, FakeServer, parse_remote, product_json, product_xml
from cli.tests.bdd.environment import Environment
from database.utils import safe_encrypt
from git.versioner.dulwich_versioner import DulwichVersioner
from utils.bundle import Bundle
from utils.version import Version


def _quoted(text: str) -> str:
    """Parse a double-quoted step value, possibly empty."""
    return text


_quoted.pattern = r'[^"]*'  # type: ignore[attr-defined] - the hook parse's custom types are read through


def step(fmt: str) -> parsers.parse:
    """Build a step parser where every ``"{name}"`` field stops at the closing double quote."""
    return parsers.parse(re.sub(r'"\{(\w+)\}"', r'"{\1:q}"', fmt), extra_types={"q": _quoted})


def names(csv: str) -> list[str]:
    """Split a comma-separated list of names written in a step."""
    return [name.strip() for name in csv.split(",") if name.strip()]


def write_product(env: Environment, directory: str, name: str, type_: str, parents: list[str]) -> Path:
    """Create a product folder holding its description.xml."""
    product_dir = env.path(directory) / name
    product_dir.mkdir(parents=True, exist_ok=True)
    (product_dir / "description.xml").write_text(product_xml(name, type_, parents), encoding="utf-8")
    return product_dir


def table_rows(env: Environment) -> list[list[str]]:
    """Split the final download table rows printed by the last command into their columns.

    In-progress rows are dropped: the terminal overwrites them (``\\r``) with the final row or blanks.
    """
    assert env.result is not None, "no command was run"
    segments = re.split(r"[\r\n]", env.result.output)
    rows = [re.split(r"\s{2,}", s.strip()) for s in segments if s.strip()]
    return [row for row in rows if row[2:3] != ["⏳ In progress"]]


# Given: environment


@given(step('the operator\'s home directory is "{path}"'))
def home_directory(env: Environment, path: str) -> None:
    """Point HOME at a sandbox directory."""
    env.path(path).mkdir(parents=True, exist_ok=True)
    env.setenv("HOME", str(env.path(path)))


@given(step('the environment variable {name} is "{value}"'))
def env_set(env: Environment, name: str, value: str) -> None:
    """Set an environment variable."""
    env.setenv(name, value)


@given(step("the environment variable {name} is not set"))
def env_unset(env: Environment, name: str) -> None:
    """Remove an environment variable."""
    env.setenv(name, None)


@given(step("the environment variable {name} is empty"))
def env_empty(env: Environment, name: str) -> None:
    """Set an environment variable to the empty string."""
    env.setenv(name, "")


# Given: filesystem


@given(step('the directory "{path}" exists'))
def directory_created(env: Environment, path: str) -> None:
    """Create a directory."""
    env.path(path).mkdir(parents=True, exist_ok=True)


@given(step('the directory "{path}" does not exist'))
def directory_absent(env: Environment, path: str) -> None:
    """Check a directory is absent before the command runs."""
    assert not env.path(path).exists()


@given(step('the file "{path}" contains "{text}"'))
def file_written(env: Environment, path: str, text: str) -> None:
    """Create a file with the given content."""
    env.path(path).parent.mkdir(parents=True, exist_ok=True)
    env.path(path).write_text(text, encoding="utf-8")


@given(step('"{path}" is a symlink to "{target}"'))
def symlink_created(env: Environment, path: str, target: str) -> None:
    """Create a symbolic link."""
    env.path(path).parent.mkdir(parents=True, exist_ok=True)
    env.path(path).symlink_to(env.path(target))


# Given: installer directory


@given(step('the installer directory "{directory}" holds the product "{name}" of type "{type_}"'))
def installed_product(env: Environment, directory: str, name: str, type_: str) -> None:
    """Create a product folder without parents."""
    write_product(env, directory, name, type_, [])


@given(step('the installer directory "{directory}" holds the product "{name}" of type "{type_}" with parents "{parents}"'))
def installed_product_with_parents(env: Environment, directory: str, name: str, type_: str, parents: str) -> None:
    """Create a product folder declaring its parents."""
    write_product(env, directory, name, type_, names(parents))


@given(step('the product "{name}" in "{directory}" was downloaded from storage at commit "{commit}" of branch "{branch}"'))
def downloaded_product(env: Environment, name: str, directory: str, commit: str, branch: str) -> None:
    """Add the description.json a storage download leaves next to description.xml."""
    product_dir = env.path(directory) / name
    if not (product_dir / "description.xml").exists():
        write_product(env, directory, name, "solution", [])
    (product_dir / "description.json").write_text(product_json(name, "", branch, commit), encoding="utf-8")


@given(step('the product "{name}" in "{directory}" is a git working copy on branch "{branch}"'))
def git_working_copy(env: Environment, name: str, directory: str, branch: str) -> None:
    """Clone the product from its GitHub remote into the installer directory, on branch."""
    bare = env.git.serve("github", name, {branch: {"description.xml": product_xml(name)}})
    target = env.path(directory) / name
    target.parent.mkdir(parents=True, exist_ok=True)
    porcelain.clone(str(bare), str(target), branch=branch.encode()).close()


@given(step('the product "{name}" in "{directory}" is a local build'))
def local_build(env: Environment, name: str, directory: str) -> None:
    """Create a product folder the way ``make`` does: description.xml without description.json."""
    write_product(env, directory, name, "solution", [])


# Given: remote sources


@given(step('the storage holds the product "{name}" version "{version}" at commit "{commit}" of branch "{branch}"'))
def storage_product(env: Environment, name: str, version: str, commit: str, branch: str) -> None:
    """Publish a product archive without parents."""
    env.storage.publish_product(name, version, branch, commit)


@given(
    step(
        'the storage holds the product "{name}" version "{version}" at commit "{commit}" of branch "{branch}" '
        'with parents "{parents}"'
    )
)
def storage_product_with_parents(
    env: Environment, name: str, version: str, commit: str, branch: str, parents: str
) -> None:
    """Publish a product archive declaring its parents."""
    env.storage.publish_product(name, version, branch, commit, names(parents))


@given(step('the storage holds the bundle "{bundle}" version "{version}" pinning:'))
def storage_bundle(env: Environment, bundle: str, version: str, datatable: list[list[str]]) -> None:
    """Publish a bundle descriptor from a ``| product | commit | branch |`` table."""
    header, *rows = datatable
    env.storage.publish_bundle(bundle, version, [dict(zip(header, row, strict=True)) for row in rows])


@given(step('the git provider "{provider}" serves the product "{name}" on branch "{branch}"'))
def git_remote(env: Environment, provider: str, name: str, branch: str) -> None:
    """Publish a product repository on a git provider, with one branch."""
    env.git.serve(provider, name, {branch: {"description.xml": product_xml(name)}})


# When


@when(step('the operator runs "{cmdline}"'))
def operator_runs(env: Environment, cmdline: str) -> None:
    """Run a console script."""
    env.run(cmdline)


@when(step('the operator interrupts "{cmdline}" with Ctrl-C'))
def operator_interrupts(env: Environment, cmdline: str) -> None:
    """Run a console script and press Ctrl-C at its first call to an external system."""
    env.interrupt()
    env.run(cmdline)


# Then: output


@then(step("the exit code is {code:d}"))
def exit_code(env: Environment, code: int) -> None:
    """Check the exit code of the last command."""
    assert env.result is not None
    assert env.result.exit_code == code, env.result.output


@then(step('the output contains "{text}"'))
def output_contains(env: Environment, text: str) -> None:
    """Check stdout and stderr together contain text."""
    assert env.result is not None
    assert text in env.result.output, f"{text!r} not in:\n{env.result.output}"


@then(step('the output does not contain "{text}"'))
def output_lacks(env: Environment, text: str) -> None:
    """Check stdout and stderr together do not contain text."""
    assert env.result is not None
    assert text not in env.result.output, f"{text!r} in:\n{env.result.output}"


@then(step('the output ends with "{text}"'))
def output_ends_with(env: Environment, text: str) -> None:
    """Check the last printed text, ignoring trailing whitespace."""
    assert env.result is not None
    assert env.result.output.rstrip().endswith(text), f"output does not end with {text!r}:\n{env.result.output}"


@then(step('the error output contains "{text}"'))
def error_output_contains(env: Environment, text: str) -> None:
    """Check stderr contains text."""
    assert env.result is not None
    assert text in env.result.stderr, f"{text!r} not in stderr:\n{env.result.stderr}"


@then(step("the output contains, in order:"))
def output_contains_in_order(env: Environment, datatable: list[list[str]]) -> None:
    """Check each ``| line |`` of the table appears in the output, after the previous one."""
    assert env.result is not None
    position = 0
    for (line,) in datatable[1:]:
        found = env.result.output.find(line, position)
        assert found >= 0, f"{line!r} not found after position {position} in:\n{env.result.output}"
        position = found + len(line)


@then(step("the output is:"))
def output_is(env: Environment, docstring: str) -> None:
    """Compare the whole output, ignoring trailing spaces on each line and trailing blank lines."""
    assert env.result is not None
    actual = "\n".join(line.rstrip() for line in env.result.output.rstrip().splitlines())
    assert actual == docstring.rstrip(), f"expected:\n{docstring}\nactual:\n{actual}"


@then(step("the output contains:"))
def output_contains_block(env: Environment, docstring: str) -> None:
    """Check a block of lines appears in the output, ignoring trailing spaces."""
    assert env.result is not None
    actual = "\n".join(line.rstrip() for line in env.result.output.splitlines())
    assert docstring.rstrip() in actual, f"expected block:\n{docstring}\nactual:\n{actual}"


# Then: download table


@then(step('the download table shows "{product}" from "{provider}" with status "{status}"'))
def table_shows(env: Environment, product: str, provider: str, status: str) -> None:
    """Check a download table row by product, provider and status."""
    rows = table_rows(env)
    assert [product, provider, status] in [row[:3] for row in rows], rows


@then(step('the download table shows "{product}" from "{provider}" with status "{status}" and details "{details}"'))
def table_shows_details(env: Environment, product: str, provider: str, status: str, details: str) -> None:
    """Check a download table row, details column included."""
    rows = table_rows(env)
    assert [product, provider, status, details] in rows, rows


@then(step('the download table does not show "{product}" from "{provider}" with status "{status}" and details "{details}"'))
def table_lacks_details(env: Environment, product: str, provider: str, status: str, details: str) -> None:
    """Check no download table row is left for a product."""
    rows = table_rows(env)
    assert product not in [row[0] for row in rows], rows


# Then: filesystem


@then(step('the directory "{path}" exists'))
def directory_exists(env: Environment, path: str) -> None:
    """Check a directory exists."""
    assert env.path(path).is_dir()


@then(step('the directory "{path}" does not exist'))
def directory_missing(env: Environment, path: str) -> None:
    """Check a directory does not exist."""
    assert not env.path(path).exists()


@then(step('the file "{path}" contains "{text}"'))
def file_contains(env: Environment, path: str, text: str) -> None:
    """Check a file holds text."""
    content = env.path(path).read_text(encoding="utf-8")
    assert text in content, content


@then(step('"{path}" is a symlink to "{target}"'))
def is_symlink(env: Environment, path: str, target: str) -> None:
    """Check a symbolic link and its target."""
    assert env.path(path).is_symlink()
    assert env.path(path).readlink() == env.path(target)


@then(step('"{path}" no longer exists'))
def no_longer_exists(env: Environment, path: str) -> None:
    """Check a path was removed (dangling symlinks included)."""
    assert not env.path(path).exists()
    assert not env.path(path).is_symlink()


# Then: downloads and git


@then(step("nothing is downloaded"))
def nothing_downloaded(env: Environment) -> None:
    """Check no archive was downloaded and no repository cloned."""
    assert env.storage.downloads == []
    assert env.git.attempts == []


@then(step('the product "{name}" is downloaded from storage at branch "{branch}"'))
def downloaded_at_branch(env: Environment, name: str, branch: str) -> None:
    """Check the product archive of branch was downloaded."""
    keys = [d.key for d in env.storage.downloads]
    assert any(k.startswith(f"{branch}/{name}/{name}_") for k in keys), keys


@then(step('the product "{name}" is downloaded from storage at commit "{commit}" of branch "{branch}"'))
def downloaded_at_commit(env: Environment, name: str, commit: str, branch: str) -> None:
    """Check the archive pinned to commit was downloaded."""
    keys = [d.key for d in env.storage.downloads]
    assert f"{branch}/{name}/{name}_{commit}.tar.gz" in keys, keys


@then(step('the product "{name}" is cloned from the git provider "{provider}" at branch "{branch}"'))
def cloned_from_provider(env: Environment, name: str, provider: str, branch: str) -> None:
    """Check a working copy of the product cloned from that provider is on branch."""
    versioner = DulwichVersioner()
    copies = [
        git_dir.parent
        for git_dir in env.root.rglob(f"{name}/.git")
        if "remotes" not in git_dir.relative_to(env.root).parts
        and parse_remote(versioner.remote_url(git_dir.parent)) == (provider, name)
    ]
    assert copies, f"no working copy of {name} cloned from {provider}"
    assert [versioner.current_branch(c) for c in copies] == [branch] * len(copies)


@then(step("the git providers are tried in order:"))
def git_providers_order(env: Environment, datatable: list[list[str]]) -> None:
    """Check the order in which the git providers were contacted."""
    tried = list(dict.fromkeys(provider for provider, _ in env.git.attempts))
    assert tried == [row[0] for row in datatable[1:]]


@then(step('the product "{name}" is downloaded from the "{area}" area of the "{backend}" storage'))
def downloaded_from_area(env: Environment, name: str, area: str, backend: str) -> None:
    """Check which storage backend and area the product archive came from."""
    sources = {(d.backend, d.area) for d in env.storage.downloads if d.key.split("/")[1] == name}
    assert sources == {(backend, area)}, sources


# Given: installer directory, 3rdparty


@given(step('the installer directory "{directory}" holds a 3rdparty with Python "{python}" and PostgreSQL "{pg}"'))
def thirdparty(env: Environment, directory: str, python: str, pg: str) -> None:
    """Lay out the 3rdparty product: versions.env, the Python site-packages and the PostgreSQL directory."""
    root = env.path(directory) / "3rdparty"
    major = ".".join(python.split(".")[:2])
    (root / "python" / "lib" / f"python{major}" / "site-packages").mkdir(parents=True, exist_ok=True)
    (root / f"postgresql-{pg}" / "bin").mkdir(parents=True, exist_ok=True)
    (root / "versions.env").write_text(
        f"PYTHON_VERSION={python}\nPYTHON_DIR=${{THIRDPARTY_HOME}}/python\n"
        f"PG_VERSION={pg}\nPG_DIR=${{THIRDPARTY_HOME}}/postgresql-{pg}\n",
        encoding="utf-8",
    )


# Given: workarea scripts and PostgreSQL


@given(step('the license "{path}" is invalid with "{message}"'))
def license_invalid(env: Environment, path: str, message: str) -> None:
    """Make kbot's license checker reject the license."""
    env.procs.on(f"python.sh -m utils.License {path}", 1, stdout=message)


@given(step('the program "{program}" exits with code {code:d}'))
def program_exits(env: Environment, program: str, code: int) -> None:
    """Make a program (basename, optionally with its first arguments) exit with code."""
    env.procs.on(program, code)



@given(step("port {port:d} on localhost is used by process {pid:d}"))
def port_in_use(env: Environment, port: int, pid: int) -> None:
    """Make another process listen on a local port."""
    env.db.ports_in_use[port] = pid


@given(step('the database "{db}" on "{host}" port {port:d} accepts the user "{user}" with the password "{password}"'))
def external_database(env: Environment, db: str, host: str, port: int, user: str, password: str) -> None:
    """Create a database owned by a login role on a PostgreSQL server."""
    server = env.db.servers.setdefault((host, port), FakeServer())
    server.roles[user] = password
    server.databases[db] = FakeDatabase(owner=user)


@given(step('the database "{db}" has tables'))
def database_has_tables(env: Environment, db: str) -> None:
    """Give a database a table in its public schema."""
    find_database(env, db).tables.add("existing_data")


@given(step('the users load creates no "admin" account'))
def no_admin_in_users_conf(env: Environment) -> None:
    """Make the kbot users load (users.conf) create no 'admin' user."""
    env.db.load_creates_admin = False


# Then: processes


@then(step('the command ran "{argv}"'))
def command_ran(env: Environment, argv: str) -> None:
    """Check a process was run whose command line starts with argv."""
    lines = [" ".join(call) for call in env.procs.calls]
    assert any(line.startswith(argv) for line in lines), "\n".join(lines)


@then(step('the command did not run "{program}"'))
def command_not_run(env: Environment, program: str) -> None:
    """Check no process of that program basename was run."""
    assert not [c for c in env.procs.calls if Path(c[0]).name == program], env.procs.calls


@then(step("the command ran, in order:"))
def commands_in_order(env: Environment, datatable: list[list[str]]) -> None:
    """Check processes whose command lines start with each ``| command |`` row ran in that order."""
    lines = [" ".join(call) for call in env.procs.calls]
    position = 0
    for (expected,) in datatable[1:]:
        found = next((i for i in range(position, len(lines)) if lines[i].startswith(expected)), None)
        assert found is not None, f"{expected!r} not run after call {position}:\n" + "\n".join(lines)
        position = found + 1


@then(step('the warning "{text}" is logged'))
def warning_logged(env: Environment, text: str) -> None:
    """Check a warning holding text was logged."""
    warnings = [env.sanitize(r.getMessage()) for r in env.logs if r.levelno == logging.WARNING]
    assert any(text in w for w in warnings), warnings


# Then: database


def find_database(env: Environment, name: str) -> FakeDatabase:
    """Return the only database of that name, on any server."""
    servers = [*env.db.servers.values(), *(c.server for c in env.db.clusters.values())]
    found = [s.databases[name] for s in servers if name in s.databases]
    assert len(found) == 1, f"{len(found)} databases named {name!r}"
    return found[0]


@then(step("the schema files were applied in order:"))
def schema_files_order(env: Environment, datatable: list[list[str]]) -> None:
    """Check exactly these SQL files were applied by psql, in this order."""
    assert env.db.applied_files == [row[0] for row in datatable[1:]], env.db.applied_files


@then(step('the password of "{login}" in "{db}" verifies "{password}"'))
def password_verifies(env: Environment, login: str, db: str, password: str) -> None:
    """Check the stored kbot password hash (SafeEncrypt) matches password, i.e. the user can log in with it."""
    stored = find_database(env, db).users.get(login)
    assert stored is not None, f"no password stored for {login!r}"
    assert safe_encrypt(password, stored) == stored



@then(step('the database "{db}" exists, owned by "{user}"'))
def database_exists(env: Environment, db: str, user: str) -> None:
    """Check a database exists with that owner."""
    assert find_database(env, db).owner == user


@then(step("the database is not contacted"))
def database_not_contacted(env: Environment) -> None:
    """Check no connection was opened to any PostgreSQL server."""
    assert env.db.connections == []


@then(step('the user "{user}" on "{host}" port {port:d} has the password "{password}"'))
def role_password(env: Environment, user: str, host: str, port: int, password: str) -> None:
    """Check the password of a PostgreSQL login role."""
    server = env.db.server(host, port)
    assert server is not None, f"no server on {host}:{port}"
    assert server.roles.get(user) == password, server.roles


@given(
    step(
        'the storage holds the product "{name}" version "{version}" at commit "{commit}" of branch "{branch}" '
        "without a description.xml"
    )
)
def storage_product_without_xml(env: Environment, name: str, version: str, commit: str, branch: str) -> None:
    """Publish a product archive that lacks its description.xml."""
    env.storage.publish_product(name, version, branch, commit, with_description_xml=False)


@then(step('the products downloaded from the "{area}" area of the "{backend}" storage are "{products}"'))
def downloaded_products(env: Environment, area: str, backend: str, products: str) -> None:
    """Check exactly these products were downloaded, all from that backend and area."""
    assert [(d.backend, d.area, d.key.split("/")[1]) for d in env.storage.downloads] == [
        (backend, area, name) for name in names(products)
    ]


@then(step("the storage is not read"))
def storage_not_read(env: Environment) -> None:
    """Check the storage provider was never used."""
    assert env.storage.downloads == []
    assert env.storage.reads == []


@then(step('the database "{db}" has the table "{table}"'))
def has_table(env: Environment, db: str, table: str) -> None:
    """Check a table exists in the public schema of a database."""
    assert table in find_database(env, db).tables


@given(step('the installer directory "{directory}" was installed from bundle "{bundle}" version "{version}"'))
def installed_from_bundle(env: Environment, directory: str, bundle: str, version: str) -> None:
    """Write the bundle.json a bundle install leaves in the installer directory."""
    descriptor = Bundle(name=bundle, version=Version.parse(version), versions=[])
    (env.path(directory) / "bundle.json").write_text(json.dumps(descriptor.to_json()), encoding="utf-8")


@given(step('the operator will answer "{answer}" to "{question}"'))
def answer(env: Environment, answer: str, question: str) -> None:
    """Queue an answer on stdin; the question is checked by the Then steps."""
    env.answers.append(answer)


@given(step('the git working copy "{path}" has uncommitted changes in "{files}"'))
def uncommitted_changes(env: Environment, path: str, files: str) -> None:
    """Append a line to files of a working copy (comma-separated) and stage them, without committing."""
    target = env.path(path)
    for file in names(files):
        with (target / file).open("a", encoding="utf-8") as f:
            f.write("\n<!-- local change -->\n")
    with Repo(str(target)) as repo:
        porcelain.add(repo, [str(target / file) for file in names(files)])


@then(step('the question "{question}" is asked'))
def question_asked(env: Environment, question: str) -> None:
    """Check the command printed the question."""
    assert env.result is not None
    assert question in env.result.output, env.result.output


@then(step("no question is asked"))
def no_question(env: Environment) -> None:
    """Check the command prompted nothing (no yes/no question, no value to type)."""
    assert env.result is not None
    assert not re.search(r"\[[yY]/[nN]\]|\]: ", env.result.output), env.result.output


def remote_of(env: Environment, path: str) -> tuple[str, str]:
    """Return (provider, repository) of the origin of a git working copy."""
    remote = parse_remote(DulwichVersioner().remote_url(env.path(path)))
    assert remote is not None, f"{path} has no GitHub/Bitbucket origin"
    return remote


def remote_head(env: Environment, path: str, branch: str) -> bytes:
    """Return the commit a branch of the origin of a git working copy points to."""
    with Repo(str(env.git.bare_path(*remote_of(env, path)))) as bare:
        return bare.refs[f"refs/heads/{branch}".encode()]


@then(step('the git working copy "{path}" is on branch "{branch}" at the head of origin'))
def at_head_of_origin(env: Environment, path: str, branch: str) -> None:
    """Check a working copy is on branch, at the commit its origin's branch points to."""
    assert DulwichVersioner().current_branch(env.path(path)) == branch
    with Repo(str(env.path(path))) as repo:
        assert repo.head() == remote_head(env, path, branch)


@given(step('a kbot workarea exists in "{directory}"'))
def kbot_workarea(env: Environment, directory: str) -> None:
    """Create a workarea: its products list and the bin/ scripts it runs."""
    workarea = env.path(directory)
    (workarea / "var").mkdir(parents=True, exist_ok=True)
    (workarea / "var" / "products.json").write_text("[]", encoding="utf-8")
    (workarea / "bin").mkdir(exist_ok=True)
    for script in ("core.sh", "kbot.sh"):
        (workarea / "bin" / script).touch(mode=0o755)


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


@given(step('a kbot workarea exists in "{directory}" with an internal database of PostgreSQL {major:d}'))
def kbot_workarea_with_db(env: Environment, directory: str, major: int) -> None:
    """Create a workarea whose stopped internal cluster holds kbot_db, initialized by a PostgreSQL major."""
    kbot_workarea(env, directory)
    pg_data = env.path(directory) / "var" / "db"
    pg_data.mkdir(parents=True, exist_ok=True)
    (pg_data / "PG_VERSION").write_text(f"{major}\n", encoding="utf-8")
    env.db.cluster(pg_data).server.databases["kbot_db"] = FakeDatabase(owner="kbot_db_user")


@then(step('the internal PostgreSQL server of "{workarea}" is running on port {port:d}'))
def internal_server_running(env: Environment, workarea: str, port: int) -> None:
    """Check the cluster of a workarea is still running when the command ends."""
    assert env.db.cluster(env.path(workarea) / "var" / "db").port == port


@then(step('the internal PostgreSQL server of "{workarea}" is stopped'))
def internal_server_still_stopped(env: Environment, workarea: str) -> None:
    """Check the cluster of a workarea is not running when the command ends."""
    assert env.db.cluster(env.path(workarea) / "var" / "db").port is None
