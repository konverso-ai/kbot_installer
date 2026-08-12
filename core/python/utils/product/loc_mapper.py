"""Localization mapper model."""

from pydantic import BaseModel


class LocMapper(BaseModel):
    """Localization mapper model."""

    en: str
    fr: str | None = None
