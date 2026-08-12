"""Tests for service.nexus_service module."""

import io
import tarfile
from collections.abc import Callable
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from service.errors import NexusHttpError
from service.nexus_service import NexusService
from utils.utils_for_unit_tests import compare

Handler = Callable[[httpx.Request], httpx.Response]


def _patched_async_client(handler: Handler):
    class _PatchedAsyncClient(httpx.AsyncClient):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = httpx.MockTransport(handler)
            super().__init__(*args, **kwargs)

    return patch("utils.async_api_client.httpx.AsyncClient", _PatchedAsyncClient)


def _build_tar_gz(content: bytes, name: str = "hello.txt") -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        info = tarfile.TarInfo(name=name)
        info.size = len(content)
        tar.addfile(info, io.BytesIO(content))
    return buffer.getvalue()


class TestNexusServiceInit:
    """Test cases for NexusService construction and client building."""

    def test_init_valid_sets_attributes(self) -> None:
        """Test __init__ stores host, auth and derives the base URL."""
        service = NexusService("nexus.example.com")

        assert compare("eq", service._host, "nexus.example.com")
        assert compare("eq", service._auth, None)
        assert compare("eq", service._base_url, "https://nexus.example.com")

    def test_get_rest_client_valid_builds_client_with_rest_prefix(self) -> None:
        """Test _get_rest_client builds an AsyncAPIClient scoped to the REST prefix."""
        seen: dict[str, object] = {}

        class _SpyClient:
            def __init__(self, base_url, prefix="api", auth=None):
                seen["base_url"] = base_url
                seen["prefix"] = prefix
                seen["auth"] = auth

        auth = object()
        service = NexusService("nexus.example.com", auth=auth)

        with patch("service.nexus_service.AsyncAPIClient", _SpyClient):
            service._get_rest_client()

        assert compare("eq", seen["base_url"], "https://nexus.example.com")
        assert compare("eq", seen["prefix"], "service/rest")
        assert compare("eq", seen["auth"], auth)


class TestNexusServiceGetFile:
    """Test cases for NexusService.get_file."""

    @pytest.mark.asyncio
    async def test_getfile_valid_adds_leading_slash(self, tmp_path: Path) -> None:
        """Test get_file prefixes the repository path with a slash when missing."""
        destination = tmp_path / "downloaded.bin"

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/repository/repo/file.txt":
                return httpx.Response(200, content=b"content")
            return httpx.Response(404)

        service = NexusService("nexus.example.com")

        with _patched_async_client(handler):
            await service.get_file("repo/file.txt", str(destination))

        assert compare("eq", destination.read_bytes(), b"content")

    @pytest.mark.asyncio
    async def test_getfile_valid_keeps_existing_leading_slash(self, tmp_path: Path) -> None:
        """Test get_file does not duplicate an existing leading slash."""
        destination = tmp_path / "downloaded.bin"

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/repository/repo/file.txt":
                return httpx.Response(200, content=b"content")
            return httpx.Response(404)

        service = NexusService("nexus.example.com")

        with _patched_async_client(handler):
            await service.get_file("/repo/file.txt", str(destination))

        assert compare("eq", destination.read_bytes(), b"content")

    @pytest.mark.asyncio
    async def test_getfile_invalid_raises_nexushttperror(self, tmp_path: Path) -> None:
        """Test get_file wraps HTTP failures into a NexusHttpError."""
        destination = tmp_path / "downloaded.bin"

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404)

        service = NexusService("nexus.example.com")

        with _patched_async_client(handler):
            with pytest.raises(NexusHttpError) as exc_info:
                await service.get_file("/repo/missing.txt", str(destination))

        assert compare("eq", exc_info.value.status_code, 404)


class TestNexusServiceListRepository:
    """Test cases for NexusService.list_repository and list_assets."""

    @pytest.mark.asyncio
    async def test_listassets_valid_delegates_to_list_repository(self) -> None:
        """Test list_assets forwards the repository name to list_repository."""
        service = NexusService("nexus.example.com")
        expected = object()

        with patch.object(
            NexusService, "list_repository", AsyncMock(return_value=expected)
        ) as mock_list_repository:
            result = await service.list_assets("kbot_raw")

        mock_list_repository.assert_awaited_once_with("kbot_raw")
        assert compare("eq", result, expected)

    @pytest.mark.asyncio
    async def test_listrepository_valid_single_page(self) -> None:
        """Test list_repository returns files from a single page of results."""

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/service/rest/v1/assets":
                return httpx.Response(
                    200,
                    json={"items": [{"path": "/repo/a.txt"}], "continuationToken": None},
                )
            return httpx.Response(404)

        service = NexusService("nexus.example.com")

        with _patched_async_client(handler):
            result = await service.list_repository("kbot_raw")

        assert compare("eq", len(result), 1)
        assert compare("eq", result.continuation_token, None)

    @pytest.mark.asyncio
    async def test_listrepository_valid_paginates_until_no_token(self) -> None:
        """Test list_repository follows continuation tokens across pages."""
        calls: list[str | None] = []

        def handler(request: httpx.Request) -> httpx.Response:
            token = request.url.params.get("continuationToken")
            calls.append(token)
            if not token:
                return httpx.Response(
                    200,
                    json={"items": [{"path": "/repo/a.txt"}], "continuationToken": "tok-1"},
                )
            return httpx.Response(
                200,
                json={"items": [{"path": "/repo/b.txt"}], "continuationToken": None},
            )

        service = NexusService("nexus.example.com")

        with _patched_async_client(handler):
            result = await service.list_repository("kbot_raw")

        assert compare("eq", len(result), 2)
        assert compare("eq", result.continuation_token, None)
        assert compare("eq", calls, [None, "tok-1"])

    @pytest.mark.asyncio
    async def test_listrepository_valid_omits_repository_param_when_empty(self) -> None:
        """Test list_repository does not send a repository filter when empty."""
        seen_params: list[dict[str, str]] = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen_params.append(dict(request.url.params))
            return httpx.Response(200, json={"items": [], "continuationToken": None})

        service = NexusService("nexus.example.com")

        with _patched_async_client(handler):
            await service.list_repository("")

        assert compare("eq", seen_params, [{}])

    @pytest.mark.asyncio
    async def test_listrepository_invalid_raises_nexushttperror(self) -> None:
        """Test list_repository wraps HTTP failures into a NexusHttpError."""

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500)

        service = NexusService("nexus.example.com")

        with _patched_async_client(handler):
            with pytest.raises(NexusHttpError) as exc_info:
                await service.list_repository("kbot_raw")

        assert compare("eq", exc_info.value.status_code, 500)


class TestNexusServiceSearch:
    """Test cases for NexusService.search."""

    @pytest.mark.asyncio
    async def test_search_valid_includes_repository_param(self) -> None:
        """Test search sends the repository filter when provided."""
        seen_params: list[dict[str, str]] = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen_params.append(dict(request.url.params))
            return httpx.Response(200, json={"items": [{"path": "/repo/a.txt"}]})

        service = NexusService("nexus.example.com")

        with _patched_async_client(handler):
            result = await service.search("kbot_raw")

        assert compare("eq", seen_params, [{"repository": "kbot_raw"}])
        assert compare("eq", len(result), 1)

    @pytest.mark.asyncio
    async def test_search_valid_omits_repository_param_when_none(self) -> None:
        """Test search omits the repository filter when none is given."""
        seen_params: list[dict[str, str]] = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen_params.append(dict(request.url.params))
            return httpx.Response(200, json={"items": []})

        service = NexusService("nexus.example.com")

        with _patched_async_client(handler):
            await service.search()

        assert compare("eq", seen_params, [{}])

    @pytest.mark.asyncio
    async def test_search_invalid_raises_nexushttperror(self) -> None:
        """Test search wraps HTTP failures into a NexusHttpError."""

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(400)

        service = NexusService("nexus.example.com")

        with _patched_async_client(handler):
            with pytest.raises(NexusHttpError) as exc_info:
                await service.search("kbot_raw")

        assert compare("eq", exc_info.value.status_code, 400)


class TestNexusServiceFileExists:
    """Test cases for NexusService.file_exists."""

    @pytest.mark.asyncio
    async def test_fileexists_valid_returns_true(self) -> None:
        """Test file_exists returns True when the HEAD request succeeds."""

        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "HEAD" and request.url.path == "/repository/repo/file.txt":
                return httpx.Response(200)
            return httpx.Response(404)

        service = NexusService("nexus.example.com")

        with _patched_async_client(handler):
            result = await service.file_exists("repo/file.txt")

        assert compare("eq", result, True)

    @pytest.mark.asyncio
    async def test_fileexists_valid_returns_false_on_http_error(self) -> None:
        """Test file_exists returns False when the HEAD request fails."""

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404)

        service = NexusService("nexus.example.com")

        with _patched_async_client(handler):
            result = await service.file_exists("/repo/missing.txt")

        assert compare("eq", result, False)


class TestNexusServiceDownloadAndExtract:
    """Test cases for NexusService.download_and_extract."""

    @pytest.mark.asyncio
    async def test_downloadandextract_valid_extracts_archive(self, tmp_path: Path) -> None:
        """Test download_and_extract downloads and extracts a tar.gz archive."""
        target_dir = tmp_path / "extracted"
        archive = _build_tar_gz(b"hello", name="hello.txt")

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/repository/repo/archive.tar.gz":
                return httpx.Response(200, content=archive)
            return httpx.Response(404)

        service = NexusService("nexus.example.com")

        with _patched_async_client(handler):
            await service.download_and_extract("repo/archive.tar.gz", str(target_dir))

        assert compare("eq", (target_dir / "hello.txt").read_bytes(), b"hello")

    @pytest.mark.asyncio
    async def test_downloadandextract_valid_creates_target_dir(self, tmp_path: Path) -> None:
        """Test download_and_extract creates the target directory if missing."""
        target_dir = tmp_path / "nested" / "extracted"
        archive = _build_tar_gz(b"hello", name="hello.txt")

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=archive)

        service = NexusService("nexus.example.com")

        with _patched_async_client(handler):
            await service.download_and_extract("/repo/archive.tar.gz", str(target_dir))

        assert compare("eq", target_dir.is_dir(), True)

    @pytest.mark.asyncio
    async def test_downloadandextract_invalid_propagates_http_error(self, tmp_path: Path) -> None:
        """Test download_and_extract propagates Nexus HTTP errors from the download step."""
        target_dir = tmp_path / "extracted"
        service = NexusService("nexus.example.com")

        with patch.object(
            NexusService,
            "get_file",
            AsyncMock(side_effect=NexusHttpError(404, "Not found")),
        ):
            with pytest.raises(NexusHttpError):
                await service.download_and_extract("/repo/missing.tar.gz", str(target_dir))
