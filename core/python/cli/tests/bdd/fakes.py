"""Fakes standing in for the systems the installer talks to: processes, object storage, git remotes.

Each fake records what the installer asked of it so that steps can assert on it,
and raises ``AssertionError("Fake<Name>: unsupported ...")`` on a call it was not
written for, so a gap in the fake fails loudly instead of passing silently.
"""

from __future__ import annotations

import io
import json
import re
import shutil
import subprocess
import tarfile
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

from dulwich import porcelain
from typing_extensions import override

from storage.base import StorageBase
from utils.bundle import Bundle
from utils.product.build import Build
from utils.product.product import Product

ProcessEffect = Callable[[list[str]], None]

# Remote hosts the git providers clone from, mapped to the provider name.
GIT_HOSTS = {"github.com": "github", "bitbucket.org": "bitbucket"}


def product_xml(name: str, type_: str = "solution", parents: list[str] | None = None) -> str:
    """Render a description.xml in the format the products ship (see ``_write_product`` in test_commands)."""
    parents_xml = ""
    if parents:
        parents_xml = "<parents>" + "".join(f'<parent name="{p}"/>' for p in parents) + "</parents>"
    return f'<product name="{name}" type="{type_}">{parents_xml}</product>'


def product_json(name: str, version: str, branch: str, commit: str, parents: list[str] | None = None) -> str:
    """Render the description.json every storage archive carries, with its build information."""
    product = Product(name=name, version=version, build=Build(branch=branch, commit=commit))
    data = product.to_json()
    data["parents"] = parents or []
    return json.dumps(data)


@dataclass
class ProcessRule:
    """Canned result of a process whose program basename matches ``match``."""

    match: str
    returncode: int = 0
    stdout: str = ""
    stderr: str = ""
    effect: ProcessEffect | None = None


@dataclass
class FakeProcesses:
    """Replace ``subprocess.run`` / ``subprocess.Popen``: record each argv and answer from rules."""

    sanitize: Callable[[str], str]
    calls: list[list[str]] = field(default_factory=list)
    rules: list[ProcessRule] = field(default_factory=list)
    interrupt: bool = False

    def on(
        self,
        match: str,
        returncode: int = 0,
        stdout: str = "",
        stderr: str = "",
        effect: ProcessEffect | None = None,
    ) -> None:
        """Declare the result of the programs whose basename is ``match`` (latest rule wins)."""
        self.rules.insert(0, ProcessRule(match, returncode, stdout, stderr, effect))

    def _answer(self, args: object) -> ProcessRule:
        """Record a call and return the rule that answers it."""
        if self.interrupt:
            self.interrupt = False
            raise KeyboardInterrupt
        if isinstance(args, (str, bytes)) or not isinstance(args, (list, tuple)):
            msg = f"FakeProcesses: unsupported non-list command {args!r}"
            raise AssertionError(msg)  # noqa: TRY004 - surfaces a fake gap, not a type check
        argv = [self.sanitize(str(arg)) for arg in args]
        self.calls.append(argv)
        rule = next((r for r in self.rules if Path(argv[0]).name == r.match), ProcessRule(argv[0]))
        if rule.effect:
            rule.effect([str(arg) for arg in args])
        return rule

    def run(self, args: object, *_: object, **kwargs: object) -> subprocess.CompletedProcess[str | bytes]:
        """Stand in for ``subprocess.run``, honouring ``check`` and ``text``/bytes output."""
        rule = self._answer(args)
        text = bool(kwargs.get("text") or kwargs.get("universal_newlines") or kwargs.get("encoding"))
        out: str | bytes = rule.stdout if text else rule.stdout.encode()
        err: str | bytes = rule.stderr if text else rule.stderr.encode()
        if kwargs.get("check") and rule.returncode:
            raise subprocess.CalledProcessError(rule.returncode, list(args), out, err)  # type: ignore[arg-type]
        return subprocess.CompletedProcess(list(args), rule.returncode, out, err)  # type: ignore[arg-type]

    def popen(self, args: object, *_: object, **__: object) -> object:
        """Stand in for ``subprocess.Popen`` until a scenario needs it."""
        if isinstance(args, list) and "hooks/" in str(args[0]):
            # dulwich runs git hooks without checking they exist and treats OSError as "no hook".
            raise FileNotFoundError(args[0])
        msg = f"FakeProcesses: unsupported Popen {args!r}"
        raise AssertionError(msg)


def _archive(files: dict[str, str]) -> bytes:
    """Build the tar.gz the storage serves, holding ``files`` (archive path to text)."""
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for name, text in files.items():
            data = text.encode()
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


@dataclass
class StorageAccess:
    """One read of the object storage: backend, area and object key."""

    backend: str
    area: str
    key: str


class FakeStorageArea(StorageBase):
    """In-memory ``StorageBase`` for one backend and area, reading from the shared ``FakeStorage``."""

    def __init__(self, store: FakeStorage, backend: str, area: str) -> None:
        """Bind the area to the shared object store."""
        self._store = store
        self._backend = backend
        self._area = area

    def _objects(self) -> dict[str, bytes]:
        """Return the objects of this area: bundles have their own area, products share the other ones."""
        return self._store.bundles if self._area == "bundles" else self._store.artifacts

    @override
    def get_name(self) -> str:
        """Name the backend, as the real storages do."""
        return self._backend

    @override
    def download(self, key: str, local_file_path: Path | str) -> None:
        """Extract the archive stored at key into the local directory, like the real backends."""
        self._store.touch()
        self._store.downloads.append(StorageAccess(self._backend, self._area, key))
        data = self._objects().get(key)
        if data is None:
            msg = f"404 Not Found: {key}"
            raise FileNotFoundError(msg)
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
            tar.extractall(local_file_path, filter="data")

    @override
    def get(self, key: str, encoding: str = "utf-8") -> str | None:
        """Return the object at key, or None when absent."""
        self._store.touch()
        self._store.reads.append(StorageAccess(self._backend, self._area, key))
        data = self._objects().get(key)
        return None if data is None else data.decode(encoding)

    @override
    def list(self, prefix: str = "") -> Iterator[str]:
        """List the keys of this area under prefix."""
        self._store.touch()
        return iter(sorted(k for k in self._objects() if k.startswith(prefix)))

    @override
    def list_files_in_folder(self, folder_path: str = "") -> Iterator[str]:
        """List the keys directly inside folder_path."""
        prefix = folder_path.rstrip("/") + "/" if folder_path else ""
        return iter([k for k in self.list(prefix) if "/" not in k[len(prefix) :]])

    @override
    def list_folders(self, path: str = "") -> Iterator[str]:
        """List the folder names directly inside path."""
        prefix = path.rstrip("/") + "/" if path else ""
        return iter(sorted({k[len(prefix) :].split("/")[0] for k in self.list(prefix) if "/" in k[len(prefix) :]}))

    @override
    def set(self, key: str, value: str | bytes, encoding: str = "utf-8") -> None:
        """Writing to storage is not something the installer does."""
        msg = f"FakeStorage: unsupported set {key!r}"
        raise AssertionError(msg)

    @override
    def delete(self, key: str) -> None:
        """Deleting from storage is not something the installer does."""
        msg = f"FakeStorage: unsupported delete {key!r}"
        raise AssertionError(msg)

    @override
    def delete_folder(self, key: str) -> None:
        """Deleting from storage is not something the installer does."""
        msg = f"FakeStorage: unsupported delete_folder {key!r}"
        raise AssertionError(msg)

    @override
    def restore_soft_deleted_blob(self, key: str) -> bool:
        """Restoring blobs is not something the installer does."""
        msg = f"FakeStorage: unsupported restore_soft_deleted_blob {key!r}"
        raise AssertionError(msg)


@dataclass
class FakeStorage:
    """Object storage holding product archives (``artifacts``) and bundle descriptors (``bundles``)."""

    artifacts: dict[str, bytes] = field(default_factory=dict)
    bundles: dict[str, bytes] = field(default_factory=dict)
    downloads: list[StorageAccess] = field(default_factory=list)
    reads: list[StorageAccess] = field(default_factory=list)
    built: list[tuple[str, str]] = field(default_factory=list)
    interrupt: bool = False

    def touch(self) -> None:
        """Raise the pending Ctrl-C on the first storage access."""
        if self.interrupt:
            self.interrupt = False
            raise KeyboardInterrupt

    def area(self, backend: str, area: str | None) -> FakeStorageArea:
        """Stand in for ``add_storage_from_config``: the area the installer asked for, on this store."""
        name = area or "default"
        self.built.append((backend, name))
        return FakeStorageArea(self, backend, name)

    def publish_product(  # noqa: PLR0913 - mirrors the published archive metadata
        self,
        name: str,
        version: str,
        branch: str,
        commit: str,
        parents: list[str] | None = None,
        type_: str = "solution",
        *,
        with_description_xml: bool = True,
    ) -> None:
        """Publish a product archive under its commit key and as the branch's latest archive."""
        files = {f"{name}/description.json": product_json(name, version, branch, commit, parents)}
        if with_description_xml:
            files[f"{name}/description.xml"] = product_xml(name, type_, parents)
        archive = _archive(files)
        for suffix in (commit, "latest"):
            self.artifacts[f"{branch}/{name}/{name}_{suffix}.tar.gz"] = archive
        self.artifacts[f"{branch}/{name}/description_latest.json"] = files[f"{name}/description.json"].encode()

    def publish_bundle(self, name: str, version: str, pins: list[dict[str, str]]) -> None:
        """Publish a bundle descriptor pinning each product to a commit of a branch."""
        bundle = Bundle(
            name=name,
            version=version,
            versions=[
                Product(name=pin["product"], build=Build(branch=pin["branch"], commit=pin["commit"])) for pin in pins
            ],
        )
        self.bundles[str(Bundle.file_name(name))] = json.dumps(bundle.to_json()).encode()


@dataclass
class FakeGitRemotes:
    """GitHub and Bitbucket served from local bare repositories, so dulwich runs for real offline."""

    root: Path
    attempts: list[tuple[str, str]] = field(default_factory=list)
    interrupt: bool = False

    def bare_path(self, provider: str, repository: str) -> Path:
        """Return the local bare repository standing for a provider's repository."""
        return self.root / "remotes" / provider / f"{repository}.git"

    def serve(self, provider: str, repository: str, branches: dict[str, dict[str, str]]) -> Path:
        """Add one commit per branch holding the given files to the provider's repository (created if needed)."""
        seed = self.root / "remotes" / ".seed" / provider / repository
        first_branch = None if seed.exists() else next(iter(branches))
        seed.mkdir(parents=True, exist_ok=True)
        repo = porcelain.open_repo(str(seed)) if first_branch is None else porcelain.init(str(seed))
        try:
            for branch, files in branches.items():
                repo.refs.set_symbolic_ref(b"HEAD", f"refs/heads/{branch}".encode())
                for name, text in files.items():
                    (seed / name).write_text(text, encoding="utf-8")
                porcelain.add(repo, [str(seed / name) for name in files])
                porcelain.commit(repo, message=branch.encode(), author=b"t <t@t>", committer=b"t <t@t>")
            if first_branch is not None:
                repo.refs.set_symbolic_ref(b"HEAD", f"refs/heads/{first_branch}".encode())
        finally:
            repo.close()
        bare = self.bare_path(provider, repository)
        shutil.rmtree(bare, ignore_errors=True)
        bare.parent.mkdir(parents=True, exist_ok=True)
        porcelain.clone(str(seed), str(bare), bare=True, errstream=io.BytesIO()).close()
        return bare

    def rewrite(self, location: str) -> str:
        """Map a GitHub/Bitbucket URL to its local bare repository, recording the attempt."""
        if self.interrupt:
            self.interrupt = False
            raise KeyboardInterrupt
        remote = parse_remote(location) if "://" in location or "@" in location else None
        if remote is None:
            return location
        self.attempts.append(remote)
        return str(self.bare_path(*remote))


def parse_remote(location: str) -> tuple[str, str] | None:
    """Return (provider, repository) of a GitHub/Bitbucket URL or of its local bare repository, else None."""
    local = re.search(r"/remotes/(\w+)/([^/]+)\.git$", location)
    if local:
        return local.group(1), local.group(2)
    parsed = urlparse(location if "://" in location else "ssh://" + location.replace(":", "/", 1))
    provider = GIT_HOSTS.get(parsed.hostname or "")
    if provider is None:
        return None
    return provider, parsed.path.rstrip("/").rsplit("/", 1)[-1].removesuffix(".git")
