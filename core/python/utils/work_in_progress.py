from typing import TYPE_CHECKING, Any, Protocol

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
