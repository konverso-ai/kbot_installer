"""Async Nexus repository service."""

import asyncio
import tempfile
from pathlib import Path

import httpx
from auth.base import HttpAuthBase
from storage.download_utils import extract_tar_gz_archive
from utils.async_api_client import AsyncAPIClient

from service.errors import NexusHttpError
from service.nexus_files import NexusFiles

REST_PREFIX = "service/rest"


class NexusService:
    """Async service for Nexus repository operations."""

    def __init__(self, host: str, auth: HttpAuthBase | None = None) -> None:
        self._host = host
        self._auth = auth
        self._base_url = f"https://{host}"

    def _get_rest_client(self) -> AsyncAPIClient:
        return AsyncAPIClient(self._base_url, prefix=REST_PREFIX, auth=self._auth)

    async def get_file(self, repository_path: str, target_file_path: str) -> httpx.Response:
        """Download a repository file to a local path."""
        if not repository_path.startswith("/"):
            repository_path = f"/{repository_path}"

        try:
            async with AsyncAPIClient(self._base_url, prefix="", auth=self._auth) as client:
                return await client.download_file(
                    target_file_path,
                    f"repository{repository_path}",
                )
        except httpx.HTTPStatusError as exc:
            raise NexusHttpError(
                exc.response.status_code,
                f"Failed to load file '{repository_path}'",
            ) from exc

    async def list_assets(self, repository_name: str = "") -> NexusFiles:
        """List assets, optionally scoped to a repository."""
        return await self.list_repository(repository_name)

    async def list_repository(self, repository_name: str) -> NexusFiles:
        """List repository assets with pagination."""
        nexus_files = NexusFiles.empty(service=self)
        continuation_token = ""

        try:
            async with self._get_rest_client() as client:
                while True:
                    params: dict[str, str] = {}
                    if repository_name:
                        params["repository"] = repository_name
                    if continuation_token:
                        params["continuationToken"] = continuation_token

                    payload = await client.get("v1/assets", params=params)
                    nexus_files.extend_from_json(payload)

                    continuation_token = nexus_files.continuation_token or ""
                    if not continuation_token:
                        break
        except httpx.HTTPStatusError as exc:
            raise NexusHttpError(exc.response.status_code) from exc

        nexus_files.continuation_token = None
        return nexus_files

    async def search(self, repository: str | None = None) -> NexusFiles:
        """Search assets in a repository."""
        params = {}
        if repository:
            params["repository"] = repository

        try:
            async with self._get_rest_client() as client:
                payload = await client.get("v1/search", params=params)
        except httpx.HTTPStatusError as exc:
            raise NexusHttpError(exc.response.status_code) from exc

        return NexusFiles.from_json(payload, service=self)

    async def file_exists(self, repository_path: str) -> bool:
        """Return True when a repository file is reachable."""
        if not repository_path.startswith("/"):
            repository_path = f"/{repository_path}"

        try:
            async with AsyncAPIClient(self._base_url, prefix="", auth=self._auth) as client:
                await client.head(f"repository{repository_path}")
        except httpx.HTTPStatusError:
            return False
        else:
            return True

    async def download_and_extract(
        self,
        repository_path: str,
        target_dir: str | Path,
    ) -> None:
        """Download a gzipped tar archive from the repository and extract it."""
        if not repository_path.startswith("/"):
            repository_path = f"/{repository_path}"

        target = Path(target_dir)
        target.mkdir(parents=True, exist_ok=True)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".tar.gz") as temp_file:
            temp_path = temp_file.name

        try:
            await self.get_file(repository_path, temp_path)
            await asyncio.to_thread(
                extract_tar_gz_archive,
                Path(temp_path),
                target,
            )
        finally:
            Path(temp_path).unlink(missing_ok=True)
