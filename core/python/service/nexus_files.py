"""Nexus files collection model."""

from __future__ import annotations

from typing import Annotated, Any, TypeAlias
from typing_extensions import Self

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

from service.nexus_file import NexusFile
from typing_extensions import override

NexusFileItems: TypeAlias = Annotated[list[NexusFile], Field(default_factory=list)]
ContinuationToken: TypeAlias = Annotated[
    str | None, Field(default=None, alias="continuationToken")
]


class NexusFiles(BaseModel):
    """Paginated collection of Nexus files with filtering utilities."""

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

    files: NexusFileItems
    continuation_token: ContinuationToken = None
    _service: Any = PrivateAttr(default=None)

    @classmethod
    def from_json(cls, data: dict[str, Any], *, service: Any) -> Self:
        instance = cls(
            files=[
                NexusFile.from_json(item, service=service)
                for item in data.get("items", [])
            ],
            continuation_token=data.get("continuationToken"),
        )
        instance._service = service
        return instance

    @classmethod
    def empty(cls, *, service: Any) -> Self:
        instance = cls()
        instance._service = service
        return instance

    def extend_from_json(self, data: dict[str, Any]) -> None:
        self.files.extend(
            NexusFile.from_json(item, service=self._service)
            for item in data.get("items", [])
        )
        self.continuation_token = data.get("continuationToken")

    def filter(
        self,
        folder_name: str | None = None,
        name: str | None = None,
        ends_with: str | None = None,
        not_ends_with: str | None = None,
        folder_starts_with: str | None = None,
        contains: str | None = None,
    ) -> NexusFiles:
        """Filter files and return a new NexusFiles list."""
        files = list(self.files)

        if folder_name:
            files = [item for item in files if item.folder_name == folder_name]

        if folder_starts_with:
            files = [
                item
                for item in files
                if item.folder_name and item.folder_name.startswith(folder_starts_with)
            ]

        if name:
            files = [item for item in files if item.file_name == name]

        if ends_with:
            files = [
                item
                for item in files
                if item.file_name and item.file_name.endswith(ends_with)
            ]

        if not_ends_with:
            files = [
                item
                for item in files
                if item.file_name and not item.file_name.endswith(not_ends_with)
            ]

        if contains:
            files = [item for item in files if item.path and contains in item.path]

        filtered = NexusFiles(files=files)
        filtered._service = self._service
        return filtered

    def latest(self) -> NexusFile | None:
        """Return the most recently modified file, if any."""
        if not self.files:
            return None
        return sorted(
            self.files, key=lambda item: item.last_modified or "", reverse=True
        )[0]

    @override
    def __iter__(self):
        return iter(self.files)

    def __len__(self) -> int:
        return len(self.files)
