"""Nexus asset checksum model."""

from typing import Annotated, Any, TypeAlias

from pydantic import BaseModel, Field
from typing_extensions import Self

Md5: TypeAlias = Annotated[str | None, Field(default=None)]
Sha1: TypeAlias = Annotated[str | None, Field(default=None)]
Sha256: TypeAlias = Annotated[str | None, Field(default=None)]
Sha512: TypeAlias = Annotated[str | None, Field(default=None)]


class Checksum(BaseModel):
    """Checksum metadata for a Nexus asset."""

    md5: Md5
    sha1: Sha1
    sha256: Sha256
    sha512: Sha512

    @classmethod
    def from_json(cls, data: dict[str, Any] | None) -> Self:
        """Build a Checksum from a Nexus API payload.

        Args:
            data: Raw checksum mapping from the Nexus API, or None.

        Returns:
            A Checksum instance populated from data, or an empty Checksum
            when data is falsy.

        """
        if not data:
            return cls()
        return cls.model_validate(data)
