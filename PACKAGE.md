# Extensible package convention

- This applies to every **new or restructured** package that products may extend, by adding or overriding implementations.
- It is the kbot counterpart of the kbot_installer "Factory + naming-convention pattern", and it uses the same `utils.factory` helpers (kbot_installer `core/python/utils/factory/`, branch `KB-20538*`).
  - kbot imports them as `utils.factory`: `utils` is a namespace package in both repos, and `bin/env.sh` puts `$KBOTINSTALLER_HOME` on `PYTHONPATH`.
- Some legacy packages use `utils.factory_class.kfactory.KFactory` + `discover_classes_from_product_folders`, or a `pkgutil.walk_packages` auto-import in an `__init__.py` (`llm/guardrails`, `search/extractor`, `security/vault`, …). They stay as they are until they're migrated. **Don't copy either pattern into a new package.**

## Naming

- **Package:** `snake_case`, **at most 3 words** (`knowledge`, `data_source`, `vector_index`).
- **Class:** `PascalCase`. **Constant:** `UPPER_CASE`.
- **Function and method:** always lowercase `snake_case` (`get_rows`, `ensure_bootstrapped`), in every Python module of kbot, inside or outside an extensible package. This rule has no exception: never create a function or method with a CamelCase name, even in a legacy module whose existing methods are CamelCase (`GetRows`, `GetConfig`), and give a `snake_case` name to any function or method you rename.
- **Concrete class:** `<Identifier><Package>` in the module `<identifier>_<package>.py`. For example, `ConfluenceKnowledge` lives in `confluence_knowledge.py` (package `search.knowledge`), and `SharepointDataSource` in `sharepoint_data_source.py` (package `search.data_source`). Only the last segment of the dotted package counts.
- **Acronyms:** the class name is derived from the module name by `utils.factory.utils.snake_to_pascal` (`"".join(w.capitalize() for w in s.split("_"))`), so acronyms are spelled as ordinary words. `pdf_extract_knowledge.py` → `PdfExtractKnowledge`, **not** `PDFExtractKnowledge`. Any other spelling makes the lookup fail with `AttributeError`.
- **Base classes, mixins and protocols:**
  - A base class ends with `Base` (`KnowledgeBase`), and a mixin ends with `Mixin` (`SearchableMixin`).
  - Protocols live in `base`, and their names must not end with the package name either.
  - So no base, mixin or protocol can ever match the `<Identifier><Package>` lookup, and the factory can't instantiate one by mistake.
- **Identifiers (`kind`):** they match `^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$`.

## Layout

```
search/knowledge/            # no __init__.py
    base.py                  # KnowledgeBase, protocols
    mixin.py                 # *Mixin classes            (optional)
    factory.py               # add_knowledge, list_knowledge_kinds, add_<kind>_knowledge helpers
    registry.py              # stored classes/instances  (optional, see "Registry and resolver")
    resolver.py              # choice rule               (optional, see "Registry and resolver")
    confluence_knowledge.py  # ConfluenceKnowledge (final)
    sharepoint_knowledge.py  # SharepointKnowledge (final)
```

- An extensible package contains **only** these modules.
  - Helpers go in `base`/`mixin`, or in another package.
  - Tests go in `tests/`, which isn't a structural module.
- `base`, `mixin`, `factory`, `registry` and `resolver` may each become a sub-package (with no `__init__.py`) once they define more than one class.
  - Inside the sub-package, put one class per module, named as the `snake_case` of the class. For example, `base/knowledge_base.py` holds `KnowledgeBase`, and `base/indexable_knowledge_base.py` holds `IndexableKnowledgeBase`.
- A concrete module **never** becomes a package.
- A concrete class is final: decorate it with `typing.final`, and never subclass it.
- To find the concrete classes, list the directory: they're the `*_<package>.py` files.

## Namespace packages and product overrides

- An extensible package has **no `__init__.py`** in any product, and neither do its parents, all the way up to the `sys.path` root.
  - If one portion has an `__init__.py`, it becomes a regular package, and the other portions stop merging.
  - kbot_installer packages are different: products don't extend them, so they keep their `__init__.py`.
- **Adding** an implementation: a product ships `core/python/search/knowledge/jira_knowledge.py`, and nothing gets registered.
- **Overriding** an implementation: a product ships a module with the same name (`confluence_knowledge.py`).
  - The kbot_installer workarea links each product's `core/python/**/*.py|*.so` into `$KBOT_HOME/core/python`, children first and parents last. The first product to provide a path wins (installer `workarea/utils.py`, `conf/rules.json`).
  - The same order is written to `var/products.json`, which `ProductList` reads.
  - So `import_module` returns the override, and code never loops over layers (site > customer > solution > framework).
- An override replaces the whole module.
  - It can't subclass or import the framework copy: the concrete class is final, and the framework copy is shadowed under the same dotted name.
  - Behaviour meant for reuse belongs in `base`/`mixin`.
- Cython builds (`.so`) work: `pkgutil.iter_modules` and `importlib.import_module` handle extension modules, and nothing depends on `__file__`.

## Factory

`factory.py` reuses `utils.factory` and exposes:
- `add_<package>(kind, **kwargs)`: builds one instance.
- `list_<package>_kinds()`: lists the kinds without importing them.
- Optionally, `add_<kind>_<package>(...)` helpers plus `add_builtin_<package>(kind, **kwargs)`, when building an instance needs intermediate objects.

Reference implementation:

```python
"""Factory for the ``search.knowledge`` package."""
import importlib
import pkgutil
from typing import cast

from search.knowledge.base import KnowledgeBase
from utils.factory import factory_method

PACKAGE = "search.knowledge"
SUFFIX = "_knowledge"


def add_knowledge(kind: str, **kwargs: object) -> KnowledgeBase:
    """Build the ``<Kind>Knowledge`` defined in ``search/knowledge/<kind>_knowledge.py``."""
    return cast("KnowledgeBase", factory_method(kind, PACKAGE, **kwargs))


def list_knowledge_kinds() -> list[str]:
    """Kinds available across all products, without importing any of them."""
    package = importlib.import_module(PACKAGE)
    return sorted({
        name.removesuffix(SUFFIX)
        for _, name, is_pkg in pkgutil.iter_modules(package.__path__)
        if not is_pkg and name.endswith(SUFFIX)
    })
```

The variant with intermediate objects follows the same shape as kbot_installer `vault/factory.py`. This one is illustrative: `add_connection` stands for whichever factory builds the dependency.

```python
from collections.abc import Callable

from utils.factory import factory_function


def add_confluence_knowledge(connection_uuid: str, **kwargs: object) -> KnowledgeBase:
    connection = add_connection("confluence", uuid=connection_uuid)   # intermediate object
    return add_knowledge("confluence", connection=connection, **kwargs)


def add_builtin_knowledge(kind: str, **kwargs: object) -> KnowledgeBase:
    builder = cast("Callable[..., KnowledgeBase]",
                   factory_function(module_name=__name__, attribute_name=f"add_{kind}_knowledge"))
    return builder(**kwargs)
```

- **The import system is the registry, and `utils.factory` is the resolver.** There's no `resolve()` function and no registration decorator.
- `utils.factory` passes errors through unchanged:

  |Exception|Cause|
  |---|---|
  |`ModuleNotFoundError`|No module for that kind, *or* the module exists but one of its own imports is missing|
  |`AttributeError`|The module has no `<Identifier><Package>` class|
  |`TypeError`|Wrong kwargs|

  It doesn't validate the kind, doesn't check `issubclass` and doesn't cache.
- **Trust boundary:** a `kind` that comes from the DB, the UI or the REST API must be checked with `kind in list_<package>_kinds()` before `add_<package>` is called. `import_module` imports whatever name it's given.
  - After that check, a `ModuleNotFoundError` means a broken module, so let it propagate.
  - Never catch it to fall back to another kind. That silent fallback is what `discover_classes_from_product_folders` does today, logging only a warning.
- Build intermediate objects (connections, transports, credentials, config parsing) in `add_<kind>_<package>` helpers, never in the callers.

## Registry and resolver (only when there is a decision)

- **`registry.py`:** create it only to **store** something the import system doesn't, such as:
  - built instances (for example, a per-uuid cache filled on the first `add_*` call);
  - classes from outside the package.
- **`resolver.py`:** create it only when a request has **several candidates** and a rule must choose between them.
  - Examples: a choice that depends on config, tenant, version or a feature flag; a computed key ("an exporter for this format and this customer"); a fallback.
  - A resolver returns a `kind` and **never instantiates**. The flow is `kind = resolve_<package>(context)`, then `add_<package>(kind, ...)`.
  - Reference: kbot_installer `git/provider/branch_resolver.py` on `KB-20538`.
- If every key maps to exactly one class and the choice depends on nothing else, write neither file; `factory.py` is enough.
- Layer priority isn't a resolver concern: product overrides already handle it (see "Namespace packages and product overrides").

## Lazy loading

- Importing `factory.py` must not import any concrete module.
- No module-level instantiation.
- No eager discovery: no `walk_packages`, no `discover_classes_from_product_folders`, no `load_classes()` at boot.
- Nothing is imported or built until something calls `add_<package>` or `resolve_<package>`. After the first import, `sys.modules` makes later imports free.
- UI selectors and admin lists use `list_<package>_kinds()`. Labels, icons and help text are keyed by `kind` (for example, the message `search.engine.<kind>.name`), so building a selector never needs the class.
- `Bot.py` must not prebuild factories. These are the **known deviations today**:
  - `Bot.InitSystems`: `CacheFactory`, `BucketStorageFactory`, `ConnectionFactory`, `MCPConfigurationFactory`, `ErrorCodeFactory`, `IntentionFactory().Load()`, `ClassifierFactory().load()`, `parsers.ParserSystem()`, `ReloadLLMs`, `VectorStoreFactory`, `VectorizerFactory`, `VectorIndexFactory`.
  - `Bot.Load`: `WObjectFactory().load_classes()`, `AutomationDataProviderFactory().load_classes()`, `KBFactory()`, `GlobalKBList().ReviewRelationships()`, `DataSourceFactory().load_classes()`, `ReportFactory().load()`.

  Before you make one of them lazy, check it for boot-time side effects: registrations, DB writes, reload broadcasts.
- Runtime systems that *must* start at boot (`MessageBroker`, `CommunicationSystem`, `SchedulerSystem`, `SecuritySystem`, `DialogSystem`) aren't factories, so this rule doesn't apply to them.

## Example: knowledge bases in `search/`

- **Today:** `KBFactory` (`search/KBBase.py`) runs in `Bot.Load` and imports every `search/*.py` from every product at boot, only to give the UI selector its `engine_name` ids. If one module is broken, it disappears and only a warning is logged.
- **Target layout:**
  ```
  search/
      knowledge/     base/  factory.py  mixin.py  confluence_knowledge.py  sharepoint_knowledge.py ...
      result/        base.py  factory.py  confluence_result.py ...
      context/       ...
      data_source/   base.py  factory.py  sharepoint_data_source.py ...
  ```
- **Usage:**
  - `add_knowledge("confluence", **body)` returns a `ConfluenceKnowledge`.
  - The selector calls `list_knowledge_kinds()`, which imports nothing.
- **Migration constraints:**
  - `engine_name` is stored in the `kbs` table and must never be renamed. Some existing ids don't fit the convention (`vector_store_kb`, `fullindexablefederatedkb`). Before they can become `kind`s, they need a DB upgrade script (`db/upgrade_N_to_N+1.sql`) and a conf migration. That work belongs to the migration, not to this convention.
  - `search/context/` has an `__init__.py` today, which holds `SearchContextRepository`. It isn't extensible under this convention until that code moves into `base`/`registry`.

## Checklist for a new extensible package

- [ ] The name is at most 3 `snake_case` words.
- [ ] There's no `__init__.py` in the package or in any of its parents.
- [ ] `base.py` holds `<Package>Base`.
- [ ] Concrete classes are `@final` `<Identifier><Package>` classes in `<identifier>_<package>.py`.
- [ ] `factory.py` copies the reference implementation (`add_<package>`, `list_<package>_kinds`), with the names replaced.
- [ ] Untrusted kinds are checked against `list_<package>_kinds()`, and nothing runs at import or at boot.
