"""Environment variable helpers for the CLI."""

from __future__ import annotations


def format_missing_env_vars_message(var_names: list[str]) -> str:
    """Build a user-facing message when required environment variables are absent."""
    vars_label = ", ".join(var_names)
    return (
        f"Missing credentials: {vars_label}. "
        "Variables must be exported to be visible to uv run "
        "(use 'export VAR=value' in ~/.zprofile or ~/.bash_profile). "
        "Verify with: env | grep NEXUS"
    )
