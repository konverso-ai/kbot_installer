"""Work-in-progress models for bundle serialization."""

from typing import TYPE_CHECKING, Any, Protocol
from collections.abc import Iterator


from typing_extensions import override

from pydantic import (
    BaseModel,
    ConfigDict,
    field_validator,
    field_serializer,
    model_validator,
    RootModel,
)

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
        if isinstance(v, str):
            v = TYPE_MAP.get(v)
        if v not in ALLOWED_TYPES:
            raise ValueError(
                f"`type` doit être l'une des classes : str, int, float, bool. Reçu : {v!r}"
            )
        return v

    @field_serializer("type")
    def serialize_type(self, v: type) -> str:
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
    root: dict[str, Setting] = {}

    @model_validator(mode="before")
    @classmethod
    def populate_from_list(cls, v: Any) -> Any:
        if isinstance(v, list):
            return {s["name"] if isinstance(s, dict) else s.name: s for s in v}
        return v

    def add(self, setting: Setting) -> None:
        self.root[setting.name] = setting

    def __getitem__(self, key: str) -> Setting:
        return self.root[key]

    def __setitem__(self, key: str, value: Setting) -> None:
        self.root[key] = value

    def __delitem__(self, key: str) -> None:
        del self.root[key]

    def __contains__(self, key: str) -> bool:
        return key in self.root

    @override
    def __iter__(self) -> Iterator[str]:
        return iter(self.root)

    def __len__(self) -> int:
        return len(self.root)

    def get(self, key: str, default: Any = None) -> Setting | None:
        return self.root.get(key, default)

    def keys(self):
        return self.root.keys()

    def values(self):
        return self.root.values()

    def items(self):
        return self.root.items()

    @override
    def __repr__(self) -> str:
        return f"Settings(root={self.root!r})"

    @override
    def __str__(self) -> str:
        return f"<Settings [{len(self.root)} setting(s)] keys={list(self.root.keys())}>"


class JsonModel(BaseModel):
    @classmethod
    def from_json(cls, data: str | bytes):
        return cls.model_validate_json(data)

    def to_json(self, indent: int | None) -> str:
        return self.model_dump_json(
            indent=indent,
            exclude_defaults=True,
            exclude_none=True,
        )
