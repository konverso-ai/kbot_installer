"""Step vocabulary shared by the KBOT-INST-0N feature files.

Quoted step values never contain a double quote, which keeps steps that only differ
by a suffix (``... of branch "dev"`` / ``... of branch "dev" with parents "kbot"``) apart.
"""

from __future__ import annotations

import re
from pathlib import Path

from dulwich import porcelain
from pytest_bdd import given, parsers, then, when

from cli.tests.bdd.fakes import parse_remote, product_json, product_xml
from cli.tests.bdd.environment import Environment
from git.versioner.dulwich_versioner import DulwichVersioner


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
