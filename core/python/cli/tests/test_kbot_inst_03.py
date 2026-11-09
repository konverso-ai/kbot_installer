"""PO sheet KBOT-INST-03 — Update: steps used by this sheet only."""

import io
import json
import logging
from pathlib import Path

from dulwich import porcelain
from dulwich.repo import Repo
from pytest_bdd import given, parsers, scenarios, then

from cli.tests.bdd.fakes import product_json, product_xml
from cli.tests.bdd.steps_common import names, remote_head, remote_of, step, table_rows, write_product
from cli.tests.bdd.environment import Environment
from utils.bundle import Bundle
from utils.product.build import Build
from utils.product.product import Product
from utils.version import Version

scenarios("features/KBOT-INST-03.feature")


def clone(env: Environment, name: str, directory: str, branch: str, files: dict[str, str]) -> Path:
    """Serve a product repository on GitHub with files on branch, and clone it."""
    bare = env.git.serve("github", name, {branch: files})
    target = env.path(directory) / name
    target.parent.mkdir(parents=True, exist_ok=True)
    porcelain.clone(str(bare), str(target), branch=branch.encode(), errstream=io.BytesIO()).close()
    return target


def push_commit(env: Environment, path: str, branch: str, files: dict[str, str]) -> None:
    """Add a commit of files on a branch of the origin of a git working copy."""
    env.git.serve(*remote_of(env, path), {branch: files})


def commit_locally(path: Path, files: dict[str, str]) -> None:
    """Write files in a working copy and commit them there."""
    for file, text in files.items():
        (path / file).parent.mkdir(parents=True, exist_ok=True)
        (path / file).write_text(text, encoding="utf-8")
    with Repo(str(path)) as repo:
        porcelain.add(repo, [str(path / file) for file in files])
        porcelain.commit(repo, message=b"local", author=b"t <t@t>", committer=b"t <t@t>")


# Given: installer directory


@given(
    step('the product "{name}" in "{directory}" was downloaded from storage at commit "{commit}" without a build branch')
)
def downloaded_without_branch(env: Environment, name: str, directory: str, commit: str) -> None:
    """Write a storage download whose description.json records no build branch."""
    product_dir = env.path(directory) / name
    if not (product_dir / "description.xml").exists():
        write_product(env, directory, name, "solution", [])
    (product_dir / "description.json").write_text(product_json(name, "", "", commit), encoding="utf-8")


# Given: storage


@given(step('the storage holds the release "{version}" of the bundle "{bundle}" pinning:'))
def storage_bundle_release(env: Environment, version: str, bundle: str, datatable: list[list[str]]) -> None:
    """Publish the descriptor of a bundle release under ``<bundle>-<version>.json``, as the bundle builds do."""
    header, *rows = datatable
    pins = [dict(zip(header, row, strict=True)) for row in rows]
    descriptor = Bundle(
        name=bundle,
        version=Version.parse(version),
        versions=[Product(name=p["product"], build=Build(branch=p["branch"], commit=p["commit"])) for p in pins],
    )
    env.storage.bundles[f"{bundle}-{version}.json"] = json.dumps(descriptor.to_json()).encode()


@given(step('the storage publishes no description next to the latest "{branch}" artifact of "{name}"'))
def no_latest_description(env: Environment, branch: str, name: str) -> None:
    """Remove the description_latest.json published next to the latest artifact of a branch."""
    del env.storage.artifacts[f"{branch}/{name}/description_latest.json"]


@given(step('moving a folder into "{path}" fails with "{message}"'))
def move_fails(env: Environment, path: str, message: str) -> None:
    """Make the first rename of another folder onto path fail, as a busy filesystem would; restoring it works."""
    target = env.path(path)
    rename = Path.rename
    failed: list[Path] = []

    def failing_rename(self: Path, destination: Path | str) -> Path:
        """Fail once when the destination is the target folder."""
        if Path(destination) == target and not failed:
            failed.append(self)
            raise OSError(16, message)
        return rename(self, destination)

    env.monkeypatch.setattr(Path, "rename", failing_rename)


# Given: git working copies


@given(step('the product "{name}" in "{directory}" is a git working copy of version "{version}" on branch "{branch}"'))
def versioned_working_copy(env: Environment, name: str, directory: str, version: str, branch: str) -> None:
    """Clone a product whose description.xml declares a version (none when empty), on branch."""
    clone(env, name, directory, branch, {"description.xml": product_xml(name, "framework", None, version)})


@given(step('the product "{name}" in "{directory}" is a git working copy on a detached HEAD'))
def detached_working_copy(env: Environment, name: str, directory: str) -> None:
    """Clone an unversioned product, then check out its commit instead of its branch."""
    target = clone(env, name, directory, "master", {"description.xml": product_xml(name, "framework")})
    with Repo(str(target)) as repo:
        head = repo.head()
    (target / ".git" / "HEAD").write_bytes(head + b"\n")


@given(
    step('the product "{name}" in "{directory}" is a git working copy whose merge of "{branch}" conflicts on "{file}"')
)
def conflicting_working_copy(env: Environment, name: str, directory: str, branch: str, file: str) -> None:
    """Clone a product, then change the same line of file locally (committed) and on its remote branch."""
    target = clone(env, name, directory, branch, {"description.xml": product_xml(name, "framework"), file: "base\n"})
    commit_locally(target, {file: "local\n"})
    push_commit(env, f"{directory}/{name}", branch, {file: "remote\n"})


@given(step('the remote of the git working copy "{path}" has a new commit on branch "{branch}"'))
def remote_new_commit(env: Environment, path: str, branch: str) -> None:
    """Add a commit on a branch of the origin of a working copy (the branch is created if needed)."""
    provider, repository = remote_of(env, path)
    seed = env.root / "remotes" / ".seed" / provider / repository
    count = len(list(seed.glob("new-*.txt")))
    push_commit(env, path, branch, {f"new-{count}.txt": f"commit {count}\n"})


@given(step('the remote of the git working copy "{path}" has the branches "{branches}"'))
def remote_branches(env: Environment, path: str, branches: str) -> None:
    """Create the missing branches on the origin of a working copy."""
    with Repo(str(env.git.bare_path(*remote_of(env, path)))) as bare:
        existing = {ref.decode() for ref in bare.refs.subkeys(b"refs/heads/")}
    for branch in names(branches):
        if branch not in existing:
            push_commit(env, path, branch, {f"{branch.replace('/', '-')}.txt": branch})


# Given: prompts


# Then: download table


@then(
    step(
        'the download table shows "{product}" from "{provider}" with status "{status}" '
        'and details starting with "{prefix}"'
    )
)
def table_shows_details_prefix(env: Environment, product: str, provider: str, status: str, prefix: str) -> None:
    """Check a table row whose details start with prefix."""
    rows = table_rows(env)
    assert any(row[:3] == [product, provider, status] and row[3:4] and row[3].startswith(prefix) for row in rows), rows


@then(step("the download table rows are, in order:"))
def table_rows_in_order(env: Environment, datatable: list[list[str]]) -> None:
    """Check the product, provider and status of every table row, in order."""
    rows = [row[:3] for row in table_rows(env) if len(row) >= 3]  # noqa: PLR2004 - product, provider, status
    assert rows == datatable[1:], rows


# Then: storage


@then(step('the bundle "{bundle}" is read from the "{area}" area of the "{backend}" storage'))
def bundle_read(env: Environment, bundle: str, area: str, backend: str) -> None:
    """Check the descriptor of a bundle was read from that backend and area."""
    reads = [(r.backend, r.area, r.key) for r in env.storage.reads]
    assert (backend, area, f"{bundle}.json") in reads, reads


@then(step('the installer directory "{directory}" is described by the bundle "{bundle}" version "{version}"'))
def described_by_bundle(env: Environment, directory: str, bundle: str, version: str) -> None:
    """Check the bundle.json of the installer directory names that bundle release."""
    descriptor = Bundle.from_json((env.path(directory) / "bundle.json").read_text(encoding="utf-8"))
    assert (descriptor.name, descriptor.version) == (bundle, Version.parse(version)), descriptor


# Then: git working copies


@then(step('the git working copy "{path}" did not fetch the new commit of "{branch}"'))
def not_fetched(env: Environment, path: str, branch: str) -> None:
    """Check neither HEAD nor the remote-tracking branch of a working copy reached its origin's branch."""
    head = remote_head(env, path, branch)
    with Repo(str(env.path(path))) as repo:
        assert repo.refs[f"refs/remotes/origin/{branch}".encode()] != head
        assert repo.head() != head


# Then: prompts, output, logs and workarea


@then(step('the question "{question}" is asked {count:d} times'))
def question_asked_times(env: Environment, question: str, count: int) -> None:
    """Check the command printed the question that many times."""
    assert env.result is not None
    assert env.result.output.count(question) == count, env.result.output


@then(parsers.parse("the output contains '{text}'"))
def output_contains_single_quoted(env: Environment, text: str) -> None:
    """Check the output contains a text holding double quotes."""
    assert env.result is not None
    assert text in env.result.output, f"{text!r} not in:\n{env.result.output}"


@then(step('the directory "{path}" is empty'))
def directory_empty(env: Environment, path: str) -> None:
    """Check a directory exists and holds nothing."""
    assert list(env.path(path).iterdir()) == []


@then(step('the warning "{text}" is not logged'))
def warning_not_logged(env: Environment, text: str) -> None:
    """Check no warning holding text was logged."""
    warnings = [env.sanitize(r.getMessage()) for r in env.logs if r.levelno == logging.WARNING]
    assert not any(text in w for w in warnings), warnings
