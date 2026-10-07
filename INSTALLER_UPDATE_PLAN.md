# Rework `kbot-installer update`: add `--installer`

## Context

`update` today only re-lays the workarea (`--workarea`). Add `--installer` to update the products in the installer directory (`-i`, default `~/dev/installer`):
- installation made from a bundle (`<installer>/bundle.json` exists, written by `downloadable/bundle_downloadable.py`) → fetch the latest bundle with the same name and same `major.minor`, then install its artifacts;
- otherwise → re-download each storage artifact at the latest commit of its branch;
- in both modes, every git working copy in the installer dir (hybrid github/bitbucket/storage installs) is updated in place: must have no staged/unstaged modifications (untracked files allowed), is checked out on the branch of its product version, then pulled. A dirty repo is reported as an error and skipped; the other products are still updated; the command exits non-zero at the end.

Decisions fixed by the user:
- Target branch of a git repo = derived from the `version` of its own `description.xml` (merged with `description.json` if present): candidates `version_to_branch(v, "dev")` then `version_to_branch(v, "prod")` (e.g. `release-2026.01-dev`, `release-2026.01`). If the current branch is a candidate, keep it; otherwise checkout the first candidate that exists locally or on `origin`. Empty version → stay on the current branch.
- "Dirty" = `RepoStatus.changed` non-empty (staged + unstaged). Untracked files do not block.
- Dirty / failing product → error row in the table, continue with the others, non-zero exit at the end.
- "Latest bundle" = highest version among `<name>-<version>.json` descriptors with the same bundle name and same `major.minor` as the cached `bundle.json`.

## Approach

Steps 1–4 are independent building blocks (tree stays green after each); step 5 composes them; step 6 wires the CLI.

### 1. Public local-copy classification — `core/python/downloadable/product_downloadable.py`
- Add module constants `LOCAL_SYMLINK = "local symlink"`, `LOCAL_GIT_WORKING_COPY = "local git working copy"`, `LOCAL_BUILD = "local build"`; `_local_copy_kind` returns them instead of literals.
- Rename staticmethod `_local_copy_kind` → `local_copy_kind` (public, used by step 5). Only callsite: line ~87 `self._local_copy_kind(path)`; update the two docstring references (class docstring line ~25, `_download_without_dependencies` docstring line ~75). `grep -rn "_local_copy_kind" core/python` must return nothing afterwards.

### 2. Product directories with their path — `core/python/installer_support/installer_service.py`
- Move the body of `load_products_from_disk` into new `InstallerService.load_product_dirs(self) -> list[tuple[Path, Product]]` (same loop, same skip rules, same debug log on load failure; appends `(item, product)`).
- `load_products_from_disk` becomes `return [product for _, product in self.load_product_dirs()]`.
- Reason: the installer update needs the directory (names can differ from the product name, e.g. `kbot_installer.bitbucket` declares `kbot_installer`).

### 3. Git/storage building blocks
- `core/python/git/versioner/factory.py`: add `add_versioner_for_repository_remote(repository_path: str | Path) -> VersionerBase` (Google docstring). Behavior:
  1. `probe = add_versioner(name="dulwich")`; `url = probe.remote_url(repository_path)`; on `(RemoteNotFoundError, VersionerError)` return `probe` (no remote: the later fetch fails with a clear `RemoteNotFoundError`, reported per product).
  2. If `detect_remote_scheme(url) is not RemoteScheme.HTTP` (import from `git.remote_url`): `return add_dulwich_versioner_for_url(url)` (SSH uses `~/.ssh` keys/agent, local paths no auth).
  3. HTTP: provider name from host — module constant `_HTTP_HOST_PROVIDERS = {"github.com": "github", "bitbucket.org": "bitbucket"}`, first host contained in `url`. `kwargs = add_credentials(provider_name, auth_type="basic").auth_kwargs()` (`from credentials import add_credentials`, same call as `ProvidersConfig.get_credentials`). If no provider matched or `kwargs` is empty → `return probe` (anonymous, public repos). Else `return add_dulwich_versioner_for_url(url, username=kwargs["username"], password=kwargs["password"])`.
  - No equivalent exists: `add_dulwich_versioner_for_repository` requires the caller to pass HTTP credentials.
- `core/python/git/provider/factory.py`: add public `build_storage_provider(storage_backend: StorageBackendEnum, config: ProvidersConfig = DEFAULT_PROVIDERS_CONFIG) -> ProviderBase`: `provider = _build_provider("storage", config, storage_backend=storage_backend)`; if `None` raise `ProviderError(f"Storage provider '{storage_backend.value}' is not configured or lacks credentials")`; return it. Do NOT use `add_selector_provider` here: its branch fallback would silently download another branch (`master`/`dev`) when the product branch is missing.

### 4. Latest bundle lookup — `core/python/downloadable/bundle_downloadable.py`
Add module function `find_latest_bundle_name(storage: StorageBase, current: Bundle) -> str` (returns the storage key stem, i.e. the value to pass as `BundleDownloadable(name=...)`, since `Bundle.file_name(name)` is `f"{name}.json"`):
- `prefix = f"{current.name}-"`; iterate `storage.list("")` (keys are relative to the `bundles` area on every backend: S3 strips the cluster prefix, Nexus the repository prefix).
- Skip keys containing `/`, not ending with `.json`, whose stem does not start with `prefix`. Parse `Version.parse(stem.removeprefix(prefix))`; skip on `(ValueError, TypeError)` and on empty versions (this also skips `ev-basic-plus-2025.03.0001` for `ev-basic`).
- Keep only `(version.major, version.minor) == (current.version.major, current.version.minor)`; return the stem with the max `Version` (use `max(..., key=...)` on the parsed version — published keys may be `2025.3.0016`, so compare parsed versions, never strings).
- No candidate → `raise ValueError(f"No bundle '{current.name}' {current.version.major}.{current.version.minor:02d}.* found in storage")`.

### 5. Installer update orchestration — new `core/python/updatable/installer_updatable.py`
Class `InstallerUpdatable` (non-strategy dispatcher, same style as `updatable/workarea_updatable.py:WorkareaUpdatable`; not registered in `UpdatableName`):

```python
class InstallerUpdatable:
    def __init__(self, installer_path: Path, storage_backend: StorageBackendEnum, *, verbose: bool = False) -> None
    def __call__(self) -> list[str]:  # names of the products whose update failed
```

`__call__`:
1. `table = InstallationTable(verbose=self.verbose)`; `entries = InstallerService(self.installer_path).load_product_dirs()`; `failed: list[str] = []`.
2. For each `(path, product)` in `entries` with `ProductDownloadable.local_copy_kind(path) == LOCAL_GIT_WORKING_COPY` → `_update_git_repository(path, product, table)`; append `path.name` to `failed` when it returns False.
3. If `(self.installer_path / LOCAL_BUNDLE_FILE_NAME).exists()` → `_update_bundle()`. Exceptions propagate (same as `install`: a failing bundle download aborts).
4. Else, for each entry: kind `None` and `(path / "description.json").exists()` → `_update_storage_artifact(path, product, table)` (append on False); kind `LOCAL_SYMLINK` or `LOCAL_BUILD` → `table.begin_installation(path.name)` + `complete_installation(product_name=path.name, provider_name="local", status="kept", details=f"Kept {kind}")`. Symlinks are never followed/pulled (they point to user-managed checkouts).
5. Return `failed`.

`_update_git_repository(path, product, table) -> bool` (provider column `"git"`, product column `path.name`); wrap steps in `try` / `except (VersionerError, ValueError, OSError) as e` → `complete_installation(..., status="error", error_message=str(e))`, return False:
1. `versioner = add_versioner_for_repository_remote(path)`.
2. `changed = versioner.status(path).changed`; if non-empty → error row `f"Uncommitted changes: {', '.join(changed[:5])}"` + `f" (+{len(changed) - 5} more)"` when more than 5; return False (repo untouched).
3. `versioner.fetch(path)`.
4. `current`: `versioner.current_branch(path)`, `None` on `DetachedHeadError`.
5. `candidates = _branch_candidates(product)` (module helper): `v = product.version.to_json_str()` (keeps `2026.01`; `to_str()` would give `2026.1`); `[]` if empty, else `list(dict.fromkeys([version_to_branch(v, "dev"), version_to_branch(v, "prod")]))` (`from installer_support.installer_utils import version_to_branch`).
6. Target: no candidates → `current` (if `None`: error `"Detached HEAD and no version in description.xml: cannot choose a branch"`); `current in candidates` → `current`; else `versioner.select_branch(path, candidates)`, `None` → error `f"None of the branches {', '.join(candidates)} exists"`.
7. `if target != current: versioner.checkout(path, target)`; `result = versioner.pull(path, target)`.
8. Row: if `target == current and result.is_fast_forward_noop` → status `"skipped"`, details `f"{target} already up to date"`; else `"success"`, details `f"{target} {(result.old_commit_id or '')[:10]} → {(result.new_commit_id or '')[:10]}"`. Return True.

`_update_storage_artifact(path, product, table) -> bool` (provider column `"storage"`); `except (ProviderError, ValueError, OSError)` → error row, return False:
1. `branch = product.build.branch if product.build else ""`; empty → error `"No build branch in description.json"`.
2. Provider built lazily once per call and cached on the instance: `build_storage_provider(self.storage_backend)` (a `ProviderError` here becomes an error row for that product; git-only installs never need storage credentials).
3. `with tempfile.TemporaryDirectory(dir=self.installer_path, prefix=".update-") as tmp:` (same filesystem → `rename` works; no `description.xml` at its top so product discovery ignores it) → `provider.clone_and_checkout(path.name, Path(tmp) / path.name, branch=branch)` (`commit_id=None` → `<branch>/<name>/<name>_latest.tar.gz`). Old folder is kept until the new one is fully downloaded (unlike `ProductDownloadable`, which removes first).
4. `new_dir = Path(tmp) / path.name`; no `new_dir / "description.xml"` → error `"Downloaded archive has no description.xml"`.
5. `new_commit` from `Product.from_json_file(new_dir / "description.json").build.commit` (empty if file/build missing); `old_commit = product.build.commit`.
6. Equal and non-empty → `"skipped"`, details `f"{branch} already at {old_commit[:10]}"`. Else `shutil.rmtree(path)`; `new_dir.rename(path)`; `"success"`, details `f"{branch} {old_commit[:10]} → {new_commit[:10]}"`. Full archive is downloaded even when unchanged: storage exposes no "latest commit" metadata.

`_update_bundle() -> None`:
1. `current = Bundle.from_json((self.installer_path / LOCAL_BUNDLE_FILE_NAME).read_text(encoding="utf-8"))`.
2. `latest = find_latest_bundle_name(build_configured_storage(self.storage_backend.value, area="bundles"), current)`; `log.info` old → new.
3. `BundleDownloadable(storage_name=self.storage_backend, name=latest, installer_dir=self.installer_path, verbose=self.verbose).download(self.installer_path)` — reuses existing behavior: overwrites `bundle.json`, skips products already at the pinned commit, replaces outdated ones, keeps git copies/local builds/symlinks (git copies were handled in step 2 of `__call__`). Products not listed in the new bundle are left as they are; missing dependencies are not resolved here in either mode.

Logger: `log = logger.get_package_logger("updatable")` (`from utils.Logger import logger`). Module + public docstrings in Google format.

### 6. CLI — `core/python/cli/commands.py` `update` (lines ~624–701)
- New options: `--installer` (flag; help: `"Update the installer directory: move a bundle install to the latest bundle of the same name and major.minor, otherwise download the latest storage artifact of each product's branch; git working copies are checked out on their version branch and pulled (they must have no uncommitted changes)."`), `--storage` (copy of the `install` option: `_STORAGE_CHOICES`, default `StorageBackendEnum.NEXUS.value`, `show_default=True`, help `"Storage backend holding bundles/artifacts for '--installer'."`), `-V/--verbose` (copy of `install`'s).
- Signature adds `installer: bool = False`, `storage: str = StorageBackendEnum.NEXUS.value`, `verbose: bool = False` (keyword-only, after `*`).
- `if not installer and not workarea:` → `UsageError("Nothing to update: specify what to update ('--installer' and/or '--workarea').")`.
- Body order: `failed = InstallerUpdatable(installer_path=installer_path, storage_backend=StorageBackendEnum(storage), verbose=verbose)()` if `installer` (else `[]`); then the existing workarea block if `workarea`; then `install_product_python_requirements(installer_path)` unless `--skip-python-requirements` (runs for either target); then if `failed`: `click.echo(f"Update finished with errors for: {', '.join(failed)}", err=True)` and `raise click.Abort`; else `click.echo("Update completed successfully.")`. The workarea is still relinked when some products failed (the failed ones are untouched on disk).
- Exceptions: add `except click.Abort: raise` before `except Exception` (`click.Abort` is an `Exception`, as in `install`); change the generic message to `f"Error updating: {e}"`.
- Docstring: describe both targets; examples `kbot-installer update --installer`, `kbot-installer update --installer --workarea --storage s3 -i ~/dev/installer -w ~/dev/work`.
- Import `from updatable.installer_updatable import InstallerUpdatable`.

## Critical files & anchors
- `core/python/downloadable/product_downloadable.py` — `_local_copy_kind` (~134): rename + constants.
- `core/python/downloadable/bundle_downloadable.py` — `LOCAL_BUNDLE_FILE_NAME`, `BundleDownloadable.__init__`/`_get_bundle` (~42–90): reused as-is; add `find_latest_bundle_name`.
- `core/python/git/versioner/dulwich_versioner.py` — `pull` (~532, fetch + merge `origin/<branch>` into HEAD, raises `MergeConflictError`), `select_branch` (~991, local or remote-tracking refs) — reason fetch precedes `select_branch`, checkout precedes pull.
- `core/python/git/provider/factory.py` — `_build_provider` (~258): wrapped by `build_storage_provider`.
- `core/python/cli/tests/test_commands.py` — `TestUpdateCommand` (~1069): extend.

## Verification
Run from `/home/konverso/dev/installer/kbot_installer`.

Tests to add (Google docstrings, `compare` from `utils.utils_for_unit_tests`, real dulwich repos built like the `upstream`/`clone` fixtures of `core/python/git/versioner/tests/test_dulwich_versioner_pull.py`, origin = local path so no auth):
- `core/python/updatable/tests/test_installer_updatable.py`:
  - clean clone on `feature` branch, `description.xml` `version="2026.01"`, upstream has `release-2026.01-dev` with a new commit → after call: `current_branch == "release-2026.01-dev"`, HEAD == upstream head, returns `[]`.
  - clone on `release-2026.01` (prod candidate) → stays on `release-2026.01` and gets the upstream commit.
  - tracked file modified → returned in failures, file content and HEAD unchanged; a second clean repo in the same installer dir is still pulled.
  - untracked file only → updated normally.
  - no version + detached HEAD → in failures.
  - storage artifact (dir with `description.xml` + `description.json` `build.branch="release-2026.01-dev"`, `commit="old"`), `updatable.installer_updatable.build_storage_provider` patched with a fake whose `clone_and_checkout(name, target, branch=...)` writes `target/description.xml` + `description.json` commit `"new"` → folder content replaced, `branch` received `"release-2026.01-dev"`; with commit `"old"` → original folder untouched (marker file still present).
  - local build (xml only) with no storage configured → `build_storage_provider` never called.
  - `bundle.json` present: patch `build_configured_storage`, `find_latest_bundle_name` (return `"ev-basic-2025.03.0017"`) and `BundleDownloadable` in `updatable.installer_updatable` → `BundleDownloadable` called with `name="ev-basic-2025.03.0017"`, `installer_dir=installer_path`; `.download(installer_path)` called; storage loop not run.
- `core/python/downloadable/tests/test_bundle_downloadable.py`: `find_latest_bundle_name` with fake storage keys `["ev-basic-2025.03.0016.json", "ev-basic-2025.3.0018.json", "ev-basic-2026.01.0001.json", "ev-basic-plus-2025.03.0099.json", "other/ev-basic-2025.03.0050.json", "ev-basic-2025.03.0017.txt"]` and current `ev-basic` 2025.03.0016 → `"ev-basic-2025.3.0018"`; no match → `ValueError`.
- `core/python/cli/tests/test_commands.py` `TestUpdateCommand`: `--installer --storage s3 -V` with `cli.commands.InstallerUpdatable` patched returning `[]` → exit 0, constructed with `installer_path=installer_dir, storage_backend=StorageBackendEnum.S3, verbose=True`, requirements called once, `WorkareaUpdatable` not called; returning `["qakeys"]` → exit != 0, output contains `"Update finished with errors for: qakeys"`; existing tests stay green (`"Nothing to update"` still matched).

Commands:
```bash
make test PKG=updatable && make test PKG=downloadable && make test PKG=cli && make test PKG=installer_support && make test PKG=git
make check && uvx tox -e py312-typecheck
```

End-to-end smoke (offline, temp dir — NEVER run against `~/dev/installer`, it holds the repo being edited):
```bash
T=$(mktemp -d); G="git -c user.email=a@b -c user.name=a"
git init -q -b release-2026.01-dev $T/up && echo '<product name="demo" version="2026.01" type="solution"/>' > $T/up/description.xml && echo a > $T/up/README && $G -C $T/up add . && $G -C $T/up commit -qm init
git clone -q $T/up $T/inst/demo && git -C $T/inst/demo checkout -qb feature
git clone -q $T/up $T/inst/dirty && echo local >> $T/inst/dirty/README
mkdir $T/inst/local && echo '<product name="local" type="solution"/>' > $T/inst/local/description.xml
echo b > $T/up/README && $G -C $T/up commit -qam upstream
uv run kbot-installer update --installer -i $T/inst --skip-python-requirements -V; echo "exit=$?"
git -C $T/inst/demo rev-parse --abbrev-ref HEAD; cat $T/inst/demo/README; cat $T/inst/dirty/README
```
Expected: rows `demo … git … success` (`release-2026.01-dev …→…`), `dirty … error … Uncommitted changes: README`, `local … kept`; stderr `Update finished with errors for: dirty`; `exit=1`; demo on `release-2026.01-dev` with README `b`; dirty README still `a`+`local`.

## Assumptions & contingencies
- The storage backend is not recorded at install time: `--storage` must match the one used by `install` (default `nexus`). Overridable later by persisting it next to `bundle.json`; not done here.
- A legacy/unparsable `bundle.json` makes `Bundle.from_json` raise: the update aborts with `Error updating: …`; no migration.
- If the `release-2026.01-dev` branch created upstream after the clone is not visible to `select_branch` in tests, the cause is the fixture (create the upstream branch before calling the updatable, never before cloning); do not add a second fetch path in production code.
