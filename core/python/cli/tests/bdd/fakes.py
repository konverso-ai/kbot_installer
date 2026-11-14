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

import psycopg
from dulwich import porcelain
from typing_extensions import override

from storage.base import StorageBase
from utils.bundle import Bundle
from utils.product.build import Build
from utils.product.product import Product

ProcessHandler = Callable[[list[str]], "tuple[int, str, str] | None"]

# Remote hosts the git providers clone from, mapped to the provider name.
GIT_HOSTS = {"github.com": "github", "bitbucket.org": "bitbucket"}


def product_xml(name: str, type_: str = "solution", parents: list[str] | None = None, version: str = "") -> str:
    """Render a description.xml in the format the products ship (see ``_write_product`` in test_commands)."""
    parents_xml = ""
    if parents:
        parents_xml = "<parents>" + "".join(f'<parent name="{p}"/>' for p in parents) + "</parents>"
    version_attr = f' version="{version}"' if version else ""
    return f'<product name="{name}" type="{type_}"{version_attr}>{parents_xml}</product>'


def schema_sql(name: str) -> str:
    """Render the db/init/db_schema.sql a product ships: one table named after it."""
    return f"CREATE TABLE {name.replace('-', '_')}_data (id int);\n"


def product_json(name: str, version: str, branch: str, commit: str, parents: list[str] | None = None) -> str:
    """Render the description.json every storage archive carries, with its build information."""
    product = Product(name=name, version=version, build=Build(branch=branch, commit=commit))
    data = product.to_json()
    data["parents"] = parents or []
    return json.dumps(data)


@dataclass
class ProcessRule:
    """Canned result of the processes matching ``match``: a program basename, optionally followed by arguments."""

    match: str
    returncode: int = 0
    stdout: str = ""
    stderr: str = ""
    handler: ProcessHandler | None = None

    def matches(self, argv: list[str]) -> bool:
        """Tell whether argv runs this program with these leading arguments."""
        program, *args = self.match.split()
        return Path(argv[0]).name == program and argv[1 : 1 + len(args)] == args


@dataclass
class FakeProcesses:
    """Replace ``subprocess.run`` / ``subprocess.Popen``: record each argv and answer from rules."""

    sanitize: Callable[[str], str]
    events: list[str]
    calls: list[list[str]] = field(default_factory=list)
    rules: list[ProcessRule] = field(default_factory=list)
    interrupt: bool = False

    def on(
        self,
        match: str,
        returncode: int = 0,
        stdout: str = "",
        stderr: str = "",
        handler: ProcessHandler | None = None,
    ) -> None:
        """Declare the result of the processes matching ``match`` (the latest rule wins).

        A handler gets the real argv and returns ``(returncode, stdout, stderr)``, or None for the canned result.
        """
        self.rules.insert(0, ProcessRule(match, returncode, stdout, stderr, handler))

    def _answer(self, args: object) -> tuple[int, str, str]:
        """Record a call and return its result."""
        if self.interrupt:
            self.interrupt = False
            raise KeyboardInterrupt
        if isinstance(args, (str, bytes)) or not isinstance(args, (list, tuple)):
            msg = f"FakeProcesses: unsupported non-list command {args!r}"
            raise AssertionError(msg)  # noqa: TRY004 - surfaces a fake gap, not a type check
        real = [str(arg) for arg in args]
        argv = [self.sanitize(arg) for arg in real]
        self.calls.append(argv)
        self.events.append("run " + " ".join(argv))
        rule = next((r for r in self.rules if r.matches(argv)), None)
        if rule is None:
            msg = f"FakeProcesses: unsupported command {argv!r}"
            raise AssertionError(msg)
        result = rule.handler(real) if rule.handler else None
        return result or (rule.returncode, rule.stdout, rule.stderr)

    def run(self, args: object, *_: object, **kwargs: object) -> subprocess.CompletedProcess[str | bytes]:
        """Stand in for ``subprocess.run``, honouring ``check`` and ``text``/bytes output."""
        returncode, stdout, stderr = self._answer(args)
        text = bool(kwargs.get("text") or kwargs.get("universal_newlines") or kwargs.get("encoding"))
        out: str | bytes = stdout if text else stdout.encode()
        err: str | bytes = stderr if text else stderr.encode()
        if kwargs.get("check") and returncode:
            raise subprocess.CalledProcessError(returncode, list(args), out, err)  # type: ignore[arg-type]
        return subprocess.CompletedProcess(list(args), returncode, out, err)  # type: ignore[arg-type]

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
            files[f"{name}/description.xml"] = product_xml(name, type_, parents, version)
        files[f"{name}/db/init/db_schema.sql"] = schema_sql(name)
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
        repo = porcelain.clone(str(seed), str(bare), bare=True, errstream=io.BytesIO())
        try:
            # A bare clone keeps the non-default branches as remote-tracking refs: publish them as branches.
            for ref, sha in repo.refs.as_dict(b"refs/remotes/origin").items():
                if ref != b"HEAD":
                    repo.refs[b"refs/heads/" + ref] = sha
        finally:
            repo.close()
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


@dataclass
class FakeDatabase:
    """One PostgreSQL database: owner, public tables, kbot users (login to password hash) and schema versions."""

    owner: str
    tables: set[str] = field(default_factory=set)
    users: dict[str, str | None] = field(default_factory=dict)
    versions: set[str] = field(default_factory=set)


@dataclass
class FakeServer:
    """One PostgreSQL server: login roles (name to password) and databases; ``trust`` accepts any password."""

    roles: dict[str, str] = field(default_factory=dict)
    databases: dict[str, FakeDatabase] = field(default_factory=dict)
    trust: bool = False


@dataclass
class FakeCluster:
    """An internal cluster: its data directory and server, running on ``port`` or stopped (None)."""

    server: FakeServer
    port: int | None = None


class FakeCursor:
    """Cursor answering exactly the statements of ``database/*.py``; any other statement fails the scenario."""

    def __init__(self, db: FakeDb, server: FakeServer, dbname: str) -> None:
        """Bind the cursor to the database it was opened on."""
        self._db, self._server, self._dbname = db, server, dbname
        self._rows: list[tuple[object, ...]] = []
        self.rowcount = 0

    def __enter__(self) -> FakeCursor:
        """Open the cursor."""
        return self

    def __exit__(self, *_: object) -> None:
        """Close the cursor."""

    def execute(self, query: object, params: tuple[object, ...] = ()) -> None:  # noqa: C901 - one branch per statement
        """Apply a statement to the fake server state."""
        statement = " ".join((query if isinstance(query, str) else query.as_string()).split())  # type: ignore[attr-defined]
        self._db.executed.append((self._dbname, statement))
        self._db.events.append(f"sql {self._dbname}: {statement}")
        database = self._server.databases.get(self._dbname)
        self._rows, self.rowcount = [], 0
        if m := re.fullmatch(r"SELECT 1 FROM pg_roles WHERE rolname = %s", statement):
            self._rows = [(1,)] if params[0] in self._server.roles else []
        elif m := re.fullmatch(r'CREATE ROLE "?([\w-]+)"? LOGIN PASSWORD \'(.*)\'', statement):
            self._server.roles[m.group(1)] = m.group(2).replace("''", "'")
        elif m := re.fullmatch(r"SELECT 1 FROM pg_database WHERE datname = %s", statement):
            self._rows = [(1,)] if params[0] in self._server.databases else []
        elif m := re.fullmatch(r'CREATE DATABASE "?([\w-]+)"? TEMPLATE "?\w+"? OWNER "?([\w-]+)"?', statement):
            self._server.databases[m.group(1)] = FakeDatabase(owner=m.group(2))
        elif re.fullmatch(r"ALTER SCHEMA public OWNER TO .*|ALTER SYSTEM SET max_connections = .*", statement):
            pass
        elif database is None:
            msg = f"FakeDb: unsupported statement outside a kbot database: {statement}"
            raise AssertionError(msg)
        elif statement.startswith("UPDATE users_im_account SET pwd = %s WHERE user_id = (SELECT user_id FROM users WHERE user_name = 'admin')"):
            if "admin" in database.users:
                database.users["admin"] = str(params[0])
                self.rowcount = 1
        elif statement == "DROP OWNED BY CURRENT_USER":
            database.tables.clear()
            database.users.clear()
            database.versions.clear()
        elif statement.startswith("CREATE TABLE IF NOT EXISTS __schema_version"):
            database.tables.add("__schema_version")
        elif statement == "SELECT version from __schema_version":
            self._rows = [(v,) for v in sorted(database.versions)]
        elif statement.startswith("INSERT INTO __schema_version (version) VALUES (%s)"):
            database.versions.add(str(params[0]))
        elif statement == "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'":
            self._rows = [(len(database.tables),)]
        else:
            msg = f"FakeDb: unsupported statement: {statement}"
            raise AssertionError(msg)

    def fetchone(self) -> tuple[object, ...] | None:
        """Return the first row of the last query."""
        return self._rows[0] if self._rows else None

    def fetchall(self) -> list[tuple[object, ...]]:
        """Return every row of the last query."""
        return self._rows


class FakeConnection:
    """psycopg connection to a fake server."""

    def __init__(self, db: FakeDb, server: FakeServer, dbname: str) -> None:
        """Bind the connection to a database of a server."""
        self._db, self._server, self._dbname = db, server, dbname
        self.autocommit = False

    def __enter__(self) -> FakeConnection:
        """Open the connection."""
        return self

    def __exit__(self, *_: object) -> None:
        """Close the connection."""

    def cursor(self) -> FakeCursor:
        """Open a cursor."""
        return FakeCursor(self._db, self._server, self._dbname)

    def commit(self) -> None:
        """Statements apply immediately: nothing to commit."""

    def close(self) -> None:
        """Nothing to release."""


@dataclass
class FakeDb:
    """PostgreSQL: external servers by (host, port), internal clusters by data directory, psql/pg_dump/pg_ctl.

    The internal server trusts every password, like a fresh ``initdb`` reached on localhost.
    """

    events: list[str]
    sanitize: Callable[[str], str]
    pg_major: str = "16"
    servers: dict[tuple[str, int], FakeServer] = field(default_factory=dict)
    clusters: dict[Path, FakeCluster] = field(default_factory=dict)
    ports_in_use: dict[int, int | None] = field(default_factory=dict)
    connections: list[tuple[str, int, str, str, str]] = field(default_factory=list)
    executed: list[tuple[str, str]] = field(default_factory=list)
    applied_files: list[str] = field(default_factory=list)
    load_creates_admin: bool = True

    def server(self, host: str, port: int) -> FakeServer | None:
        """Return the server answering on host:port, if any."""
        if host == "localhost":
            running = [c.server for c in self.clusters.values() if c.port == port]
            if running:
                return running[0]
        return self.servers.get((host, port))

    def connect(self, *, host: str, port: int, dbname: str, user: str, password: str, **_: object) -> FakeConnection:
        """Stand in for ``psycopg.connect``."""
        self.connections.append((host, port, dbname, user, password))
        server = self.server(host, port)
        if server is None:
            msg = f'connection to server at "{host}", port {port} failed: Connection refused'
            raise psycopg.OperationalError(msg)
        if not server.trust and server.roles.get(user) != password:
            msg = f'connection to server at "{host}", port {port} failed: FATAL:  password authentication failed for user "{user}"'
            raise psycopg.OperationalError(msg)
        if dbname != "postgres" and dbname not in server.databases:
            msg = f'connection to server at "{host}", port {port} failed: FATAL:  database "{dbname}" does not exist'
            raise psycopg.OperationalError(msg)
        return FakeConnection(self, server, dbname)

    def cluster(self, pg_data: Path) -> FakeCluster:
        """Return the internal cluster of a data directory, created on first use."""
        return self.clusters.setdefault(pg_data, FakeCluster(FakeServer(trust=True)))

    def pg_ctl(self, argv: list[str]) -> tuple[int, str, str]:
        """Answer ``pg_ctl initdb|status|start|stop -D <data>``."""
        pg_data = Path(argv[argv.index("-D") + 1])
        action = next(a for a in ("initdb", "status", "start", "stop") if a in argv)
        cluster = self.cluster(pg_data)
        if action == "initdb":
            pg_data.mkdir(parents=True, exist_ok=True)
            (pg_data / "PG_VERSION").write_text(self.pg_major + "\n", encoding="utf-8")
        elif action == "status":
            return (0 if cluster.port is not None else 3), "", ""
        elif action == "start":
            options = " ".join(argv[i + 1] for i, a in enumerate(argv) if a == "-o")
            cluster.port = int(re.search(r"-p(\d+)", options).group(1))  # type: ignore[union-attr]
        else:
            cluster.port = None
        return 0, "", ""

    def _target(self, argv: list[str]) -> FakeDatabase | None:
        """Return the database a psql/pg_dump command line points at."""
        server = self.server(argv[argv.index("-h") + 1], int(argv[argv.index("-p") + 1]))
        name = argv[argv.index("-d") + 1] if "-d" in argv else argv[-1]
        return None if server is None else server.databases.get(name)

    def psql(self, argv: list[str]) -> tuple[int, str, str]:
        """Answer ``psql -f <file>``: a file containing SYNTAX ERROR fails, else its CREATE TABLEs are applied."""
        path = Path(argv[argv.index("-f") + 1])
        database = self._target(argv)
        if database is None:
            return 2, "", "psql: error: connection to server failed"
        content = path.read_text(encoding="utf-8")
        if "SYNTAX ERROR" in content:
            return 3, "", f'psql:{self.sanitize(str(path))}:1: ERROR:  syntax error at or near "SYNTAX"'
        self.applied_files.append(self.sanitize(str(path)))
        database.tables.update(re.findall(r"CREATE TABLE (?:IF NOT EXISTS )?(\w+)", content, re.IGNORECASE))
        return 0, "", ""

    def pg_dump(self, argv: list[str]) -> tuple[int, str, str]:
        """Answer ``pg_dump -f <file> <db>``: write the tables of the database as CREATE TABLE statements."""
        database = self._target(argv)
        if database is None:
            return 1, "", "pg_dump: error: connection to server failed"
        path = Path(argv[argv.index("-f") + 1])
        path.write_text("".join(f"CREATE TABLE {t} (id int);\n" for t in sorted(database.tables)), encoding="utf-8")
        return 0, "", ""

    def load(self, _argv: list[str]) -> None:
        """Answer the kbot data load: users.conf creates the kbot 'admin' user in every kbot database."""
        for server in [*self.servers.values(), *(c.server for c in self.clusters.values())]:
            for database in server.databases.values():
                database.tables.update({"users", "users_im_account"})
                if self.load_creates_admin:
                    database.users.setdefault("admin", None)
