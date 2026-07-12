"""Work-in-progress models for bundle serialization."""

from collections.abc import Iterator
from typing import TYPE_CHECKING, Any, Protocol

from pydantic import (
    BaseModel,
    ConfigDict,
    RootModel,
    field_serializer,
    field_validator,
    model_validator,
)
from typing_extensions import override

if TYPE_CHECKING:
    from utils.bundle import Bundle


class From(Protocol):
    """From protocol."""

    def from_json(self, json_content: str | dict[str, Any]) -> "Bundle":
        """Create Bundle from JSON content."""

    def from_xml(self, xml_content: str) -> "Bundle":
        """Create Bundle from XML content."""


class To(Protocol):
    """To protocol."""

    def to_json(self) -> str:
        """Convert Bundle to JSON string."""

    def to_xml(self) -> str:
        """Convert Bundle to XML string."""


ALLOWED_TYPES = (str, int, float, bool)
TYPE_MAP = {"str": str, "int": int, "float": float, "bool": bool}


class Setting(BaseModel):
    """A named, typed configuration setting with an optional set of choices.

    Attributes:
        name: Identifier of the setting.
        type: Python type the value must conform to (str, int, float, or bool).
        value: Current value of the setting.
        default: Fallback value used when `value` is not set.
        choices: Allowed values, or None if unrestricted.
        multiple: Whether the setting accepts an iterable of values instead of one.

    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    type: Any
    value: Any = None
    default: Any = None
    choices: list[Any] | None = None
    multiple: bool = False

    @staticmethod
    def _strict_isinstance(val: Any, t: type) -> bool:
        return isinstance(val, t) and not (t is int and isinstance(val, bool))

    @staticmethod
    def _is_valid_iterable(val: Any) -> bool:
        return not isinstance(val, (str, bytes)) and hasattr(val, "__iter__")

    @field_validator("type", mode="before")
    @classmethod
    def validate_type_field(cls, v: Any) -> type:
        """Coerce the `type` field to an allowed Python type.

        Args:
            v: Raw value, either a type name (e.g. `"int"`) or an actual type.

        Returns:
            The resolved type.

        Raises:
            ValueError: If the resolved type is not one of str, int, float, bool.

        """
        if isinstance(v, str):
            v = TYPE_MAP.get(v)
        if v not in ALLOWED_TYPES:
            raise ValueError(
                f"`type` doit être l'une des classes : str, int, float, bool. Reçu : {v!r}"
            )
        return v

    @field_serializer("type")
    def serialize_type(self, v: type) -> str:
        """Serialize the `type` field to its class name."""
        return v.__name__

    def _validate_field(self, val: Any, label: str) -> None:
        if val is None:
            return

        if self.multiple and not self._is_valid_iterable(val):
            raise ValueError(
                f"`{label}` doit être un itérable (list, tuple…) avec multiple=True, "
                f"reçu {type(val).__name__!r}"
            )

        items = list(val) if self.multiple else [val]

        bad_types = [v for v in items if not self._strict_isinstance(v, self.type)]
        if bad_types:
            raise ValueError(
                f"`{label}` contient des valeurs de mauvais type "
                f"(attendu {self.type.__name__}) : {bad_types}"
            )

        choices = self.choices
        if choices is not None:
            bad_choices = [v for v in items if v not in choices]
        else:
            bad_choices = []
        if bad_choices:
            raise ValueError(
                f"`{label}` contient des valeurs hors choices {self.choices} : {bad_choices}"
            )

    @model_validator(mode="after")
    def validate_setting(self) -> "Setting":
        """Ensure a value is set and that value/default/choices are consistent.

        Falls back `value` to `default` when only the latter is provided, and
        checks that `default`, `value`, and `choices` all match the declared type.

        Returns:
            The validated setting.

        Raises:
            ValueError: If neither `value` nor `default` is set, or if any of them
                is inconsistent with `type` or `choices`.

        """
        if self.value is None and self.default is None:
            raise ValueError("Au moins `value` ou `default` doit être défini.")

        if self.value is None and self.default is not None:
            self.value = self.default

        if self.choices is not None:
            bad = [c for c in self.choices if not self._strict_isinstance(c, self.type)]
            if bad:
                raise ValueError(
                    f"`choices` contient des éléments invalides pour le type "
                    f"{self.type.__name__} : {bad}"
                )

        self._validate_field(self.default, "default")
        self._validate_field(self.value, "value")

        return self

    @override
    def __repr__(self) -> str:
        return (
            f"Setting(name={self.name!r}, type={self.type.__name__}, value={self.value!r}, "
            f"default={self.default!r}, choices={self.choices!r}, multiple={self.multiple})"
        )

    @override
    def __str__(self) -> str:
        mode = "multiple" if self.multiple else "simple"
        return f"<Setting {self.name!r} [{self.type.__name__} / {mode}] value={self.value!r} default={self.default!r}>"


class Settings(RootModel[dict[str, Setting]]):
    """A dict-like collection of `Setting` objects keyed by name."""

    root: dict[str, Setting] = {}

    @model_validator(mode="before")
    @classmethod
    def populate_from_list(cls, v: Any) -> Any:
        """Convert a list of settings into a dict keyed by setting name.

        Args:
            v: Raw input value, either already a mapping or a list of `Setting`
                instances/dicts.

        Returns:
            The value unchanged if it is not a list, otherwise a dict mapping
            each setting's name to itself.

        """
        if isinstance(v, list):
            return {s["name"] if isinstance(s, dict) else s.name: s for s in v}
        return v

    def add(self, setting: Setting) -> None:
        """Add or replace a setting, keyed by its name.

        Args:
            setting: Setting to store.

        """
        self.root[setting.name] = setting

    def __getitem__(self, key: str) -> Setting:
        """Return the setting stored under `key`."""
        return self.root[key]

    def __setitem__(self, key: str, value: Setting) -> None:
        """Store a setting under `key`."""
        self.root[key] = value

    def __delitem__(self, key: str) -> None:
        """Delete the setting stored under `key`."""
        del self.root[key]

    def __contains__(self, key: str) -> bool:
        """Return whether a setting named `key` is present."""
        return key in self.root

    @override
    def __iter__(self) -> Iterator[str]:
        return iter(self.root)

    def __len__(self) -> int:
        """Return the number of settings."""
        return len(self.root)

    def get(self, key: str, default: Any = None) -> Setting | None:
        """Return the setting named `key`, or `default` if absent.

        Args:
            key: Name of the setting to look up.
            default: Value returned when the setting is not present.

        Returns:
            The matching setting, or `default`.

        """
        return self.root.get(key, default)

    def keys(self):
        """Return the names of all settings."""
        return self.root.keys()

    def values(self):
        """Return all `Setting` values."""
        return self.root.values()

    def items(self):
        """Return (name, setting) pairs for all settings."""
        return self.root.items()

    @override
    def __repr__(self) -> str:
        return f"Settings(root={self.root!r})"

    @override
    def __str__(self) -> str:
        return f"<Settings [{len(self.root)} setting(s)] keys={list(self.root.keys())}>"


class JsonModel(BaseModel):
    """Pydantic model mixin adding JSON (de)serialization helpers."""

    @classmethod
    def from_json(cls, data: str | bytes):
        """Build a model instance from JSON data.

        Args:
            data: JSON document to parse.

        Returns:
            The validated model instance.

        """
        return cls.model_validate_json(data)

    def to_json(self, indent: int | None) -> str:
        """Serialize the model to a JSON string, omitting defaults and nulls.

        Args:
            indent: Number of spaces used for indentation, or None for compact
                output.

        Returns:
            The JSON representation of the model.

        """
        return self.model_dump_json(
            indent=indent,
            exclude_defaults=True,
            exclude_none=True,
        )
