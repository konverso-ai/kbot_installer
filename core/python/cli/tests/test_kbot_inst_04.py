"""PO sheet KBOT-INST-04 — Release upgrade: steps used by this sheet only."""

import io
import json
import re
import tarfile
from pathlib import Path

import pytest
from dulwich import porcelain
from pytest_bdd import given, scenarios, then

from cli.tests.bdd.fakes import product_xml
from cli.tests.bdd.steps_common import names, step
from cli.tests.bdd.environment import Environment
from git.versioner.dulwich_versioner import DulwichVersioner

scenarios("features/KBOT-INST-04.feature")

# Questions 'upgrade' may ask, as click prints them.
_PROMPT = re.compile(r"\[y/N\]: |\[Y/n\]: |\]: ")


@pytest.fixture
def pulls() -> list[tuple[str, str]]:
    """Collect the (working copy folder, branch) of every git pull."""
    return []


@pytest.fixture(autouse=True)
def upgrade_fakes(env: Environment, pulls: list[tuple[str, str]]) -> None:
    """Add the fakes 'upgrade' needs on top of the shared ones.

    - ``bin/dump_db.sh -f <file>`` writes the tables of the workarea's internal database as SQL.
    - git pulls are recorded.
    """

    def dump_db(argv: list[str]) -> tuple[int, str, str]:
        """Dump the workarea's internal database into the -f file."""
        cluster = env.db.clusters.get(Path(argv[0]).parent.parent / "var" / "db")
        tables = sorted({t for d in cluster.server.databases.values() for t in d.tables}) if cluster else []
        path = Path(argv[argv.index("-f") + 1])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(f"CREATE TABLE {t} (id int);\n" for t in tables) or "-- empty\n", encoding="utf-8")
        return 0, "", ""

    env.procs.on("dump_db.sh", handler=dump_db)
    pull = DulwichVersioner.pull

    def recording_pull(self: DulwichVersioner, repository_path: str | Path, branch: str) -> object:
        """Record the pull, then pull."""
        pulls.append((env.sanitize(str(repository_path)), branch))
        return pull(self, repository_path, branch)

    env.monkeypatch.setattr(DulwichVersioner, "pull", recording_pull)


def matching(env: Environment, pattern: str) -> list[Path]:
    """Return the paths matching a step path whose ``<placeholder>`` parts stand for a timestamp or anything."""
    parts = re.split(r"<(\w+)>", pattern)
    regex = "".join(
        re.escape(p) if i % 2 == 0 else (r"\d{8}_\d{6}" if p in {"timestamp", "YYYYMMDD_HHMMSS"} else ".*")
        for i, p in enumerate(parts)
    )
    root = env.path(parts[0].rsplit("/", 1)[0])
    return [p for p in root.rglob("*") if re.fullmatch(regex, env.sanitize(str(p)))]


def asked(env: Environment, question: str) -> bool:
    """Tell whether the last command prompted the question."""
    assert env.result is not None
    return re.search(re.escape(question) + r" \[[^\]]*\]: ", env.result.output) is not None


# Given


@given(step('the product "{name}" in "{directory}" is at version "{version}"'))
def product_version(env: Environment, name: str, directory: str, version: str) -> None:
    """Set the version the product's description.json records."""
    path = env.path(directory) / name / "description.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["version"] = version
    path.write_text(json.dumps(data), encoding="utf-8")


@given(step('the installer directory "{directory}" was not installed from a bundle'))
def not_installed_from_bundle(env: Environment, directory: str) -> None:
    """Check the installer directory holds no bundle.json."""
    assert not (env.path(directory) / "bundle.json").exists()


@given(step('the git provider "{provider}" serves the product "{name}" on the branches "{branches}"'))
def git_remote_branches(env: Environment, provider: str, name: str, branches: str) -> None:
    """Publish a product repository with one commit per branch; the first branch is origin's HEAD."""
    env.git.serve(provider, name, {b: {"description.xml": product_xml(name)} for b in names(branches)})


@given(step('the product "{name}" in "{directory}" is a git working copy of the git provider "{provider}" on branch "{branch}"'))
def git_clone_on_branch(env: Environment, name: str, directory: str, provider: str, branch: str) -> None:
    """Clone a repository the provider already serves, then check out branch."""
    target = env.path(directory) / name
    target.parent.mkdir(parents=True, exist_ok=True)
    porcelain.clone(str(env.git.bare_path(provider, name)), str(target), branch=branch.encode(), errstream=io.BytesIO()).close()


@given(step('the git working copy "{path}" has the local branch "{branch}" that origin does not have'))
def local_only_branch(env: Environment, path: str, branch: str) -> None:
    """Create a branch in the working copy only."""
    porcelain.branch_create(str(env.path(path)), branch)


@given(step('the git working copy "{path}" records no default branch for origin'))
def no_origin_head(env: Environment, path: str) -> None:
    """Forget origin's HEAD, as a clone made without it does."""
    with porcelain.open_repo_closing(str(env.path(path))) as repo:
        repo.refs.remove_if_equals(b"refs/remotes/origin/HEAD", None)


@given(step('the storage archive of "{name}" on branch "{branch}" holds the file "{file}" containing "{text}"'))
def archive_file(env: Environment, name: str, branch: str, file: str, text: str) -> None:
    """Add a file to every archive of the product on branch."""
    for key in [k for k in env.storage.artifacts if k.startswith(f"{branch}/{name}/") and k.endswith(".tar.gz")]:
        buffer = io.BytesIO()
        with (
            tarfile.open(fileobj=io.BytesIO(env.storage.artifacts[key]), mode="r:gz") as source,
            tarfile.open(fileobj=buffer, mode="w:gz") as target,
        ):
            for member in source.getmembers():
                target.addfile(member, source.extractfile(member))
            data = text.encode()
            info = tarfile.TarInfo(f"{name}/{file}")
            info.size = len(data)
            target.addfile(info, io.BytesIO(data))
        env.storage.artifacts[key] = buffer.getvalue()


@given(step('the workarea "{directory}" holds the broken symlink "{rel}"'))
def broken_symlink(env: Environment, directory: str, rel: str) -> None:
    """Leave a link to a file that no longer exists in the workarea."""
    link = env.path(directory) / rel
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(env.path("/home/kbot/dev/installer/removed-product/conf") / link.name)


# Then


@then(step('the question "{question}" is not asked'))
def question_not_asked(env: Environment, question: str) -> None:
    """Check the last command did not prompt the question."""
    assert not asked(env, question), env.result.output if env.result else None


@then(step('the only question asked is "{question}"'))
def only_question(env: Environment, question: str) -> None:
    """Check the last command prompted exactly one question, this one."""
    assert env.result is not None
    assert len(_PROMPT.findall(env.result.output)) == 1, env.result.output
    assert asked(env, question), env.result.output


@then(step("no process is run"))
def no_process(env: Environment) -> None:
    """Check no program was run at all."""
    assert env.procs.calls == []


@then(step('no command starting with "{argv}" ran'))
def command_not_ran(env: Environment, argv: str) -> None:
    """Check no process was run whose command line starts with argv."""
    lines = [" ".join(call) for call in env.procs.calls]
    assert not [line for line in lines if line.startswith(argv)], "\n".join(lines)


@then(step('the database is dumped to "{path}"'))
def dumped_to(env: Environment, path: str) -> None:
    """Check dump_db.sh wrote the backup file (``<YYYYMMDD_HHMMSS>`` stands for the time of the run)."""
    files = matching(env, path)
    assert len(files) == 1, files
    dumps = [c[1:] for c in env.procs.calls if Path(c[0]).name == "dump_db.sh"]
    assert dumps == [["-f", env.sanitize(str(files[0]))]], dumps


@then(step('the git working copy "{path}" is on branch "{branch}"'))
def on_branch(env: Environment, path: str, branch: str) -> None:
    """Check the branch a working copy (``<timestamp>`` allowed in path) is on."""
    copies = matching(env, path) if "<" in path else [env.path(path)]
    assert len(copies) == 1, copies
    assert DulwichVersioner().current_branch(copies[0]) == branch


@then(step('the git working copy "{path}" is not pulled'))
def not_pulled(env: Environment, path: str, pulls: list[tuple[str, str]]) -> None:
    """Check no pull was made in the working copy."""
    assert [p for p in pulls if p[0] == path] == []


@then(step('a directory matching "{pattern}" exists'))
def directory_matches(env: Environment, pattern: str) -> None:
    """Check one directory matches the path (``<timestamp>`` stands for the time of the run)."""
    found = [p for p in matching(env, pattern) if p.is_dir()]
    assert len(found) == 1, found


@then(step('no directory matches "{pattern}"'))
def no_directory_matches(env: Environment, pattern: str) -> None:
    """Check no directory matches the path (``<anything>`` stands for any text)."""
    assert [p for p in matching(env, pattern) if p.is_dir()] == []
