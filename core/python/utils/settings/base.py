"""Settings protocol for repository configuration export."""

from typing import Any, Protocol


class Settings(Protocol):
    """Repository settings exportable to conf and JSON formats."""

    def to_conf(self) -> str:
        """Return settings as a kbot.conf string."""

    def to_json(self) -> str | dict[str, Any]:
        """Return settings as a JSON string or dictionary."""
