"""Product categories container model."""

from typing import Annotated

from pydantic import BaseModel, BeforeValidator, Field

from utils.as_list import as_list
from utils.product.category import Category


class Categories(BaseModel):
    """Product categories container."""

    category: Annotated[list[Category], BeforeValidator(as_list)] = Field(
        default_factory=list
    )
