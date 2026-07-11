import asyncio
import tempfile
from collections.abc import Iterator
from pathlib import Path
from types import TracebackType
from typing import Any

import aiofiles
import httpx

from auth.base import HttpAuthBase
from storage.download_utils import extract_tar_gz_archive


class AsyncAPIClient:
    def __init__(
        self,
        base_url: str,
        prefix: str = "api",
        auth: HttpAuthBase | None = None,
    ) -> None:
        self.__base_url = (prefix and f"{base_url}/{prefix}") or base_url
        self.__auth = auth
        self.__client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "AsyncAPIClient":
        """Build the httpx client with the provided auth."""
        self.__client = httpx.AsyncClient(
            base_url=self.__base_url,
            auth=self.__auth,
            timeout=30,
            follow_redirects=True,
        )
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Close the manager."""
        if self.__client:
            await self.__client.aclose()

    async def get(
        self, endpoint: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Make a GET request."""
        if not self.__client:
            msg = "Client not initialized. Use 'async with'."
            raise RuntimeError(msg)

        response = await self.__client.get(endpoint, params=params)
        response.raise_for_status()
        return response.json()

    async def head(
        self, endpoint: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Make a HEAD request."""
        if not self.__client:
            msg = "Client not initialized. Use 'async with'."
            raise RuntimeError(msg)

        response = await self.__client.head(endpoint, params=params)
        response.raise_for_status()
        return {}

    async def post(self, endpoint: str, data: dict[str, Any]) -> dict[str, Any]:
        """Make a POST request."""
        if not self.__client:
            msg = "Client not initialized. Use 'async with'."
            raise RuntimeError(msg)

        # Use json= to let httpx automatically add Content-Type: application/json
        response = await self.__client.post(endpoint, json=data)
        response.raise_for_status()
        return response.json()

    async def put(self, endpoint: str, data: dict[str, Any]) -> dict[str, Any]:
        """Make a PUT request."""
        if not self.__client:
            msg = "Client not initialized. Use 'async with'."
            raise RuntimeError(msg)

        # Use json= to let httpx automatically add Content-Type: application/json
        response = await self.__client.put(endpoint, json=data)
        response.raise_for_status()
        return response.json()

    async def patch(self, endpoint: str, data: dict[str, Any]) -> dict[str, Any]:
        """Make a PATCH request."""
        if not self.__client:
            msg = "Client not initialized. Use 'async with'."
            raise RuntimeError(msg)

        # Use json= to let httpx automatically add Content-Type: application/json
        response = await self.__client.patch(endpoint, json=data)
        response.raise_for_status()
        return response.json()

    async def delete(self, endpoint: str, **kwargs) -> dict[str, Any]:
        """Make a DELETE request."""
        if not self.__client:
            msg = "Client not initialized. Use 'async with'."
            raise RuntimeError(msg)

        response = await self.__client.delete(endpoint, **kwargs)
        response.raise_for_status()
        if response.status_code == 204:
            return {}
        return response.json()

    async def get_multiple(self, endpoints: Iterator[str]) -> list[dict[str, Any]]:
        """Retrieve multiple endpoints in parallel."""
        if not self.__client:
            msg = "Client not initialized. Use 'async with'."
            raise RuntimeError(msg)

        tasks = (self.get(endpoint) for endpoint in endpoints)
        return await asyncio.gather(*tasks)

    async def post_multiple(
        self, requests: Iterator[tuple[str, dict[str, Any]]]
    ) -> list[dict[str, Any]]:
        """Send multiple POST requests in parallel.

        Args:
            requests: List of tuples (endpoint, data)

        Example:
            await client.post_multiple([
                ('/users', {'name': 'Alice'}),
                ('/users', {'name': 'Bob'}),
                ('/users', {'name': 'Charlie'})
            ])

        """
        if not self.__client:
            msg = "Client not initialized"
            raise RuntimeError(msg)

        tasks = (self.post(endpoint, data) for endpoint, data in requests)
        return await asyncio.gather(*tasks)

    async def post_multiple_semaphore(
        self,
        requests: list[tuple[str, dict[str, object]]],
        max_concurrent: int = 50,
    ) -> list[object]:
        if not self.__client:
            msg = "Client not initialized"
            raise RuntimeError(msg)

        semaphore = asyncio.Semaphore(max_concurrent)

        async def fetch_with_semaphore(coro):
            async with semaphore:
                return await coro

        results = await asyncio.gather(
            *(fetch_with_semaphore(r) for r in requests), return_exceptions=True
        )

        return results

    async def post_multiple_batches(
        self,
        requests: list[tuple[str, dict[str, object]]],
        max_concurrent: int = 10,
        batch_size: int = 50,
    ) -> list[object]:
        if not self.__client:
            msg = "Client not initialized"
            raise RuntimeError(msg)

        from more_itertools import batched

        r = []
        for batch in batched(requests, batch_size):
            r.extend(
                await self.post_multiple_semaphore(
                    requests=list(batch), max_concurrent=max_concurrent
                )
            )
        return r

    async def upload_file(
        self, file_name: str, folder_uuid: str, override: bool = True
    ):
        if not self.__client:
            msg = "Client not initialized. Use 'async with'."
            raise RuntimeError(msg)

        with open(file_name, "rb") as fd:
            files_dict = {"ufile": fd}
            data = {
                "folder_uuid": folder_uuid,
                "override": override,
            }
            response = await self.__client.post(
                "files/",
                data=data,
                files=files_dict,
            )
            response.raise_for_status()
            return response

    async def download_file(self, file_name: str, endpoint: str) -> httpx.Response:
        if not self.__client:
            msg = "Client not initialized. Use 'async with'."
            raise RuntimeError(msg)

        async with self.__client.stream("GET", endpoint) as response:
            response.raise_for_status()
            async with aiofiles.open(file_name, "wb") as fd:
                async for chunk in response.aiter_bytes():
                    await fd.write(chunk)
            return response

    async def download_and_untar_file(
        self, target_dir: str | Path, endpoint: str
    ) -> None:
        if not self.__client:
            msg = "Client not initialized. Use 'async with'."
            raise RuntimeError(msg)

        destination = Path(target_dir)
        destination.mkdir(parents=True, exist_ok=True)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".tar.gz") as temp_file:
            temp_path = temp_file.name

        try:
            await self.download_file(temp_path, endpoint)
            await asyncio.to_thread(
                extract_tar_gz_archive,
                Path(temp_path),
                destination,
            )
        finally:
            Path(temp_path).unlink(missing_ok=True)
