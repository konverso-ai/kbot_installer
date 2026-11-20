"""Product parents container model."""

from typing import Annotated

from pydantic import BaseModel, BeforeValidator, Field

from utils.as_list import as_list
from utils.product.parent import Parent


class Parents(BaseModel):
    """Product parents container."""

    parent: Annotated[list[Parent], BeforeValidator(as_list)] = Field(
        default_factory=list
    )
