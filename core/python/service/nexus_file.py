"""Nexus file model."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, computed_field
from typing_extensions import Self, override

from service.checksum import Checksum
from service.errors import NexusHttpError

if TYPE_CHECKING:
    from service.nexus_service import NexusService

FileId: TypeAlias = Annotated[str | None, Field(default=None)]
DownloadUrl: TypeAlias = Annotated[str | None, Field(default=None, alias="downloadUrl")]
Path: TypeAlias = Annotated[str | None, Field(default=None)]
Repository: TypeAlias = Annotated[str | None, Field(default=None)]
Format: TypeAlias = Annotated[str | None, Field(default=None)]
ChecksumField: TypeAlias = Annotated[Checksum, Field(default_factory=Checksum)]
ContentType: TypeAlias = Annotated[str | None, Field(default=None, alias="contentType")]
LastModified: TypeAlias = Annotated[
    str | None, Field(default=None, alias="lastModified")
]
LastDownloaded: TypeAlias = Annotated[
    str | None, Field(default=None, alias="lastDownloaded")
]
Uploader: TypeAlias = Annotated[str | None, Field(default=None)]
UploaderIp: TypeAlias = Annotated[str | None, Field(default=None, alias="uploaderIp")]
FileSize: TypeAlias = Annotated[int, Field(default=0, alias="fileSize")]
BlobCreated: TypeAlias = Annotated[str | None, Field(default=None, alias="blobCreated")]
BlobStoreName: TypeAlias = Annotated[
    str | None, Field(default=None, alias="blobStoreName")
]
BlobUpdated: TypeAlias = Annotated[str | None, Field(default=None, alias="blobUpdated")]
BlobRef: TypeAlias = Annotated[str | None, Field(default=None, alias="blobRef")]
LastVerified: TypeAlias = Annotated[
    str | None, Field(default=None, alias="lastVerified")
]
Raw: TypeAlias = Annotated[dict[str, Any], Field(default_factory=dict)]


class NexusFile(BaseModel):
    """Nexus asset metadata bound to a service for download operations."""

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

    download_url: DownloadUrl
    path: Path
    id: FileId
    repository: Repository
    format: Format
    checksum: ChecksumField
    content_type: ContentType
    last_modified: LastModified
    last_downloaded: LastDownloaded
    uploader: Uploader
    uploader_ip: UploaderIp
    file_size: FileSize
    blob_created: BlobCreated
    blob_store_name: BlobStoreName
    blob_updated: BlobUpdated
    blob_ref: BlobRef
    last_verified: LastVerified
    raw: Raw

    _service: NexusService = PrivateAttr()

    @classmethod
    def from_json(cls, data: dict[str, Any], *, service: NexusService) -> Self:
        """Build a NexusFile from a Nexus API payload.

        Args:
            data: Raw asset mapping from the Nexus API.
            service: Service instance used to perform later download calls.

        Returns:
            A NexusFile instance bound to service.

        """
        payload = dict(data)
        payload["checksum"] = Checksum.from_json(data.get("checksum"))
        instance = cls.model_validate(payload)
        # Setting the class's own PrivateAttr on a freshly built instance from
        # within its own factory classmethod; not an external encapsulation break.
        instance._service = service  # noqa: SLF001
        return instance

    @override
    def __str__(self) -> str:
        return f"NexusFile({self.path})"

    @override
    def __repr__(self) -> str:
        return str(self)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def folder_name(self) -> str | None:
        """Return the folder portion of the normalized asset path."""
        normalized = self._normalized_path()
        if not normalized:
            return None
        return normalized.rsplit("/", 1)[0]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def file_name(self) -> str | None:
        """Return the file name portion of the normalized asset path."""
        normalized = self._normalized_path()
        if not normalized:
            return None
        return normalized.rsplit("/", 1)[-1]

    def _normalized_path(self) -> str | None:
        if not self.path:
            return None
        return self.path.lstrip("/")

    async def download(self, target: str) -> None:
        """Download this file to the target path."""
        normalized = self._normalized_path()
        if not normalized:
            msg = "Asset has no path"
            raise NexusHttpError(400, msg)
        repository = self.repository or ""
        await self._service.get_file(f"/{repository}/{normalized}", target)
