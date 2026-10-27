"""Product build metadata model."""

from pydantic import BaseModel


class Build(BaseModel):
    """Build model."""

    timestamp: str = ""
    branch: str = ""
    commit: str = ""
