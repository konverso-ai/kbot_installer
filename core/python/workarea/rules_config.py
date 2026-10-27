"""Loading of the default workarea layout rules (``conf/rules.json``).

Mirrors the dev/installed path resolution used by
``git.provider.config._resolve_default_providers_config_path``: ``conf/rules.json``
lives at the repository root in a source checkout, and under
``installer/<name>/conf/rules.json`` once packaged (see the
``force-include`` mapping in ``pyproject.toml``).
"""

from pathlib import Path

from workarea.workarea_rule import WorkareaRule, WorkareaRules

DEFAULT_RULES_RELATIVE_PATH = Path("conf") / "rules.json"
INSTALLED_RULES_GLOB = "installer/*/conf/rules.json"


def _resolve_default_rules_path() -> Path:
    """Locate the default workarea rules file in dev or installed layouts.

    Returns:
        Path to ``conf/rules.json``, found either in the source tree (an
        ancestor of this module) or in an installed package layout.

    Raises:
        FileNotFoundError: If no matching rules file could be located.

    """
    for parent in Path(__file__).resolve().parents:
        dev_candidate = parent / DEFAULT_RULES_RELATIVE_PATH
        if dev_candidate.is_file():
            return dev_candidate

        for installed_candidate in sorted(parent.glob(INSTALLED_RULES_GLOB)):
            if installed_candidate.is_file():
                return installed_candidate

    msg = f"Could not find {DEFAULT_RULES_RELATIVE_PATH} or {INSTALLED_RULES_GLOB}"
    raise FileNotFoundError(msg)


DEFAULT_RULES_PATH = _resolve_default_rules_path()


def load_default_rules(path: Path | None = None) -> list[WorkareaRule]:
    """Load workarea layout rules from a JSON file.

    Args:
        path: Path to the JSON rules file. Defaults to ``conf/rules.json``,
            resolved via `DEFAULT_RULES_PATH`.

    Returns:
        The parsed list of workarea layout rules, in file order.

    """
    rules_path = path or DEFAULT_RULES_PATH
    return list(WorkareaRules.from_json(rules_path.read_text(encoding="utf-8")))
