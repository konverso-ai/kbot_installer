"""Settings protocol for repository configuration export."""

from typing import Any, Protocol

from pydantic import BaseModel


Simple = str | int | float | None
Choice = list[Simple]
Choices = list[Choice]


class Value(BaseModel):
    value: Simple


class NamedValue(Value):
    name: str


class SingleChoice(BaseModel):
    pass


class MultipleChoice(BaseModel):
    pass


class Settings(Protocol):
    """Repository settings exportable to conf and JSON formats."""

    def to_conf(self) -> str:
        """Return settings as a kbot.conf string."""

    def to_json(self) -> str | dict[str, Any]:
        """Return settings as a JSON string or dictionary."""
