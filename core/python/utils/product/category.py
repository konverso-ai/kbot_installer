"""Product category model."""

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class Category(BaseModel):
    """Product category."""

    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(
        validation_alias=AliasChoices("@name", "name"),
        serialization_alias="@name",
    )
