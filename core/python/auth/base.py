"""Base model for authentication fields."""

from typing import Annotated, TypeAlias

from pydantic import BaseModel, Field, SecretStr

HeaderName: TypeAlias = Annotated[str, Field(default="Authorization")]
Prefix: TypeAlias = Annotated[str, Field(default="")]
Secret: TypeAlias = Annotated[SecretStr, Field(default=SecretStr(""))]
RequiredSecret: TypeAlias = Annotated[SecretStr, Field(min_length=1)]


class AuthBase(BaseModel):
    """Shared authentication fields for header-based auth."""

    header_name: HeaderName
    prefix: Prefix
    secret: Secret
