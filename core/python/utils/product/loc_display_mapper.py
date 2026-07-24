"""Localization display mapper model."""

from pydantic import BaseModel

from utils.product.loc_mapper import LocMapper


class LocDisplayMapper(BaseModel):
    """Localization display mapper model."""

    name: LocMapper | None = None
    description: LocMapper | None = None
