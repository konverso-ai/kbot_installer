"""Tests for utils.async_api_client module."""

import io
import tarfile
from collections.abc import Callable, Iterator
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
from pydantic import SecretStr

from auth.bearer_auth import BearerAuth
from utils.async_api_client import AsyncAPIClient
from utils.utils_for_unit_tests import compare

Handler = Callable[[httpx.Request], httpx.Response]


def _patched_async_client(handler: Handler):
    class _PatchedAsyncClient(httpx.AsyncClient):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = httpx.MockTransport(handler)
            super().__init__(*args, **kwargs)

    return patch("utils.async_api_client.httpx.AsyncClient", _PatchedAsyncClient)


@pytest.mark.parametrize(
    "base_url, prefix, expected_base_url",
    [
        ("https://example.com", "api", "https://example.com/api"),
        ("https://example.com", "", "https://example.com"),
    ],
)
@pytest.mark.asyncio
async def test_asyncapiclient_valid_builds_base_url(
    base_url: str, prefix: str, expected_base_url: str
) -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={})

    class _CapturingAsyncClient(httpx.AsyncClient):
        def __init__(self, *args, **kwargs):
            seen["base_url"] = kwargs.get("base_url")
            kwargs["transport"] = httpx.MockTransport(handler)
            super().__init__(*args, **kwargs)

    with patch("utils.async_api_client.httpx.AsyncClient", _CapturingAsyncClient):
        async with AsyncAPIClient(base_url, prefix=prefix):
            pass

    assert compare("eq", seen["base_url"], expected_base_url)


@pytest.mark.asyncio
async def test_aenter_valid_passes_auth_and_client_options() -> None:
    auth = BearerAuth(secret=SecretStr("token"))
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={})

    class _CapturingAsyncClient(httpx.AsyncClient):
        def __init__(self, *args, **kwargs):
            seen.update(kwargs)
            kwargs.pop("auth", None)
            kwargs["transport"] = httpx.MockTransport(handler)
            super().__init__(*args, **kwargs)

    with patch("utils.async_api_client.httpx.AsyncClient", _CapturingAsyncClient):
        async with AsyncAPIClient("https://example.com", prefix="", auth=auth) as client:
            assert compare("eq", type(client), AsyncAPIClient)

    assert compare("eq", seen["auth"], auth)
    assert compare("eq", seen["timeout"], 30)
    assert compare("eq", seen["follow_redirects"], True)


@pytest.mark.asyncio
async def test_aexit_valid_closes_client() -> None:
    closed: list[bool] = []

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={})

    class _TrackingAsyncClient(httpx.AsyncClient):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = httpx.MockTransport(handler)
            super().__init__(*args, **kwargs)

        async def aclose(self) -> None:
            closed.append(True)
            await super().aclose()

    with patch("utils.async_api_client.httpx.AsyncClient", _TrackingAsyncClient):
        async with AsyncAPIClient("https://example.com", prefix=""):
            pass

    assert compare("eq", closed, [True])


@pytest.mark.asyncio
async def test_get_valid_returns_json() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET" and request.url.path == "/items":
            return httpx.Response(200, json={"id": 1})
        return httpx.Response(404)

    with _patched_async_client(handler):
        async with AsyncAPIClient("https://example.com", prefix="") as client:
            result = await client.get("items", params={"q": "x"})

    assert compare("eq", result, {"id": 1})


@pytest.mark.asyncio
async def test_head_valid_returns_empty_dict() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "HEAD" and request.url.path == "/items":
            return httpx.Response(200)
        return httpx.Response(404)

    with _patched_async_client(handler):
        async with AsyncAPIClient("https://example.com", prefix="") as client:
            result = await client.head("items")

    assert compare("eq", result, {})


@pytest.mark.asyncio
async def test_post_valid_returns_json() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/items":
            return httpx.Response(201, json={"created": True})
        return httpx.Response(404)

    with _patched_async_client(handler):
        async with AsyncAPIClient("https://example.com", prefix="") as client:
            result = await client.post("items", {"name": "alice"})

    assert compare("eq", result, {"created": True})


@pytest.mark.asyncio
async def test_put_valid_returns_json() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "PUT" and request.url.path == "/items/1":
            return httpx.Response(200, json={"updated": True})
        return httpx.Response(404)

    with _patched_async_client(handler):
        async with AsyncAPIClient("https://example.com", prefix="") as client:
            result = await client.put("items/1", {"name": "bob"})

    assert compare("eq", result, {"updated": True})


@pytest.mark.asyncio
async def test_patch_valid_returns_json() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "PATCH" and request.url.path == "/items/1":
            return httpx.Response(200, json={"patched": True})
        return httpx.Response(404)

    with _patched_async_client(handler):
        async with AsyncAPIClient("https://example.com", prefix="") as client:
            result = await client.patch("items/1", {"name": "carol"})

    assert compare("eq", result, {"patched": True})


@pytest.mark.asyncio
async def test_delete_valid_returns_empty_dict_on_204() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "DELETE" and request.url.path == "/items/1":
            return httpx.Response(204)
        return httpx.Response(404)

    with _patched_async_client(handler):
        async with AsyncAPIClient("https://example.com", prefix="") as client:
            result = await client.delete("items/1")

    assert compare("eq", result, {})


@pytest.mark.asyncio
async def test_delete_valid_returns_json_on_body() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "DELETE" and request.url.path == "/items/1":
            return httpx.Response(200, json={"deleted": True})
        return httpx.Response(404)

    with _patched_async_client(handler):
        async with AsyncAPIClient("https://example.com", prefix="") as client:
            result = await client.delete("items/1")

    assert compare("eq", result, {"deleted": True})


@pytest.mark.asyncio
async def test_getmultiple_valid_returns_parallel_results() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            name = request.url.path.strip("/")
            return httpx.Response(200, json={"name": name})
        return httpx.Response(404)

    with _patched_async_client(handler):
        async with AsyncAPIClient("https://example.com", prefix="") as client:
            results = await client.get_multiple(iter(["a", "b"]))

    assert compare("eq", results, [{"name": "a"}, {"name": "b"}])


@pytest.mark.asyncio
async def test_postmultiple_valid_returns_parallel_results() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(201, json={"ok": True})
        return httpx.Response(404)

    with _patched_async_client(handler):
        async with AsyncAPIClient("https://example.com", prefix="") as client:
            results = await client.post_multiple(
                iter([("users", {"name": "alice"}), ("users", {"name": "bob"})])
            )

    assert compare("eq", results, [{"ok": True}, {"ok": True}])


@pytest.mark.asyncio
async def test_postmultiplesemaphore_valid_runs_coroutines() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={})

    async def task(value: int) -> int:
        return value

    with _patched_async_client(handler):
        async with AsyncAPIClient("https://example.com", prefix="") as client:
            results = await client.post_multiple_semaphore(
                [task(1), task(2)],
                max_concurrent=1,
            )

    assert compare("eq", results, [1, 2])


@pytest.mark.asyncio
async def test_postmultiplebatches_valid_processes_batches() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={})

    async def task(value: int) -> int:
        return value

    with _patched_async_client(handler):
        async with AsyncAPIClient("https://example.com", prefix="") as client:
            results = await client.post_multiple_batches(
                [task(1), task(2), task(3)],
                max_concurrent=2,
                batch_size=2,
            )

    assert compare("eq", results, [1, 2, 3])


@pytest.mark.asyncio
async def test_uploadfile_valid_posts_multipart(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.txt"
    file_path.write_text("content", encoding="utf-8")
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/files/":
            seen["folder_uuid"] = request.read().decode("utf-8", errors="replace")
            return httpx.Response(201, json={"uploaded": True})
        return httpx.Response(404)

    with _patched_async_client(handler):
        async with AsyncAPIClient("https://example.com", prefix="") as client:
            response = await client.upload_file(
                str(file_path),
                folder_uuid="folder-1",
                override=False,
            )

    assert compare("eq", response.status_code, 201)
    assert compare("in", "folder-1", seen["folder_uuid"])


def _build_tar_gz(content: bytes, name: str = "hello.txt") -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        info = tarfile.TarInfo(name=name)
        info.size = len(content)
        tar.addfile(info, io.BytesIO(content))
    return buffer.getvalue()


@pytest.mark.asyncio
async def test_downloadfile_valid_writes_streamed_content(tmp_path: Path) -> None:
    destination = tmp_path / "downloaded.bin"

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET" and request.url.path == "/files/1":
            return httpx.Response(200, content=b"file-content")
        return httpx.Response(404)

    with _patched_async_client(handler):
        async with AsyncAPIClient("https://example.com", prefix="") as client:
            response = await client.download_file(str(destination), "files/1")

    assert compare("eq", response.status_code, 200)
    assert compare("eq", destination.read_bytes(), b"file-content")


@pytest.mark.asyncio
async def test_downloadanduntarfile_valid_extracts_streamed_archive(tmp_path: Path) -> None:
    target_dir = tmp_path / "extracted"
    archive = _build_tar_gz(b"hello", name="hello.txt")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET" and request.url.path == "/archives/pkg.tar.gz":
            return httpx.Response(200, content=archive)
        return httpx.Response(404)

    with _patched_async_client(handler):
        async with AsyncAPIClient("https://example.com", prefix="") as client:
            await client.download_and_untar_file(target_dir, "archives/pkg.tar.gz")

    extracted = target_dir / "hello.txt"
    assert compare("eq", extracted.read_bytes(), b"hello")


@pytest.mark.asyncio
async def test_downloadfile_invalid_raises_on_http_error(tmp_path: Path) -> None:
    destination = tmp_path / "downloaded.bin"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    with _patched_async_client(handler):
        async with AsyncAPIClient("https://example.com", prefix="") as client:
            with pytest.raises(httpx.HTTPStatusError):
                await client.download_file(str(destination), "files/missing")


@pytest.mark.asyncio
async def test_downloadanduntarfile_invalid_raises_on_http_error(tmp_path: Path) -> None:
    target_dir = tmp_path / "extracted"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    with _patched_async_client(handler):
        async with AsyncAPIClient("https://example.com", prefix="") as client:
            with pytest.raises(httpx.HTTPStatusError):
                await client.download_and_untar_file(target_dir, "archives/missing.tar.gz")


@pytest.mark.parametrize(
    "method_name, args",
    [
        ("get", ("items",)),
        ("head", ("items",)),
        ("post", ("items", {"a": 1})),
        ("put", ("items", {"a": 1})),
        ("patch", ("items", {"a": 1})),
        ("delete", ("items",)),
        ("get_multiple", (iter(["items"]),)),
        ("post_multiple", (iter([("items", {"a": 1})]),)),
        ("post_multiple_semaphore", ([],)),
        ("post_multiple_batches", ([],)),
        ("upload_file", ("file.txt", "folder-1")),
        ("download_file", ("file.txt", "files/1")),
        ("download_and_untar_file", ("/tmp/target", "archives/pkg.tar.gz")),
    ],
)
@pytest.mark.asyncio
async def test_asyncapiclient_invalid_raises_without_context(
    method_name: str, args: tuple
) -> None:
    client = AsyncAPIClient("https://example.com", prefix="")

    with pytest.raises(RuntimeError):
        await getattr(client, method_name)(*args)
