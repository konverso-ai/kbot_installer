"""XML writer implementation."""

from pathlib import Path

from utils.path_utils import ensure_path
from utils.work_in_progress import To


class XmlWriter:
    """Serialize models with a ``to_xml`` method to XML files."""

    def write(self, obj: To, file_path: str | Path) -> None:
        """Write a model instance to an XML file.

        Args:
            obj: Object instance exposing ``to_xml()``.
            file_path: Destination XML file path.

        Raises:
            TypeError: If *obj* does not implement ``To.to_xml()``.
        """
        try:
            xml_content = obj.to_xml()
        except AttributeError as exc:
            raise TypeError(
                f"{type(obj).__name__} does not implement to_xml()"
            ) from exc
        path = ensure_path(file_path)
        path.write_text(xml_content, encoding="utf-8")
