"""Pydantic model for Git commit author identity."""

from typing import Annotated, TypeAlias

from pydantic import BaseModel, Field, computed_field

AuthorName: TypeAlias = Annotated[str, Field(min_length=1)]
AuthorEmail: TypeAlias = Annotated[str, Field(min_length=1)]


class Author(BaseModel):
    """Git commit author in ``Name <email>`` format."""

    name: AuthorName
    email: AuthorEmail

    @computed_field  # type: ignore[prop-decorator]
    @property
    def formatted(self) -> str:
        """Return the author string in Git's ``Name <email>`` format."""
        return f"{self.name} <{self.email}>"

    def to_str(self) -> str:
        """Return the author as a string for Dulwich commit metadata."""
        return self.formatted

    def to_bytes(self) -> bytes:
        """Return the author as bytes for Dulwich commit metadata."""
        return self.formatted.encode()
