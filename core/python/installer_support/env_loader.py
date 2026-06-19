"""Environment variable helpers for the CLI."""

from __future__ import annotations

import os

# Legacy variable names mapped to the names expected by provider config.
_ENV_ALIASES: dict[str, tuple[str, ...]] = {
    "NEXUS_USERNAME": ("NEXUS_USER",),
}


def get_env_var(name: str) -> str | None:
    """Read an environment variable, including configured legacy aliases."""
    value = os.getenv(name)
    if value:
        return value

    for alias in _ENV_ALIASES.get(name, ()):
        alias_value = os.getenv(alias)
        if alias_value:
            return alias_value

    return None


def format_missing_env_vars_message(var_names: list[str]) -> str:
    """Build a user-facing message when required environment variables are absent."""
    vars_label = ", ".join(var_names)
    return (
        f"Missing credentials: {vars_label}. "
        "Variables must be exported to be visible to uv run "
        "(use 'export VAR=value' in ~/.zprofile or ~/.bash_profile). "
        "Verify with: env | grep NEXUS"
    )
