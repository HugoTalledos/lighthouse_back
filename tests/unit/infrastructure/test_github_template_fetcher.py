from __future__ import annotations
import io
import os
import tarfile
import httpx
import pytest
from pytest_httpx import HTTPXMock
from src.agent.tools.landing_builder.infrastructure.github_template_fetcher import GithubTemplateFetcher


def _fake_tarball(wrapper: str, files: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for rel_path, content in files.items():
            info = tarfile.TarInfo(name=f"{wrapper}/{rel_path}")
            info.size = len(content)
            tar.addfile(info, io.BytesIO(content))
    return buffer.getvalue()


async def test_fetch_strips_wrapper_directory(httpx_mock: HTTPXMock):
    tarball = _fake_tarball(
        "landing-template-main",
        {"package.json": b'{"name": "template"}', "src/pages/index.astro": b"<div/>"},
    )
    httpx_mock.add_response(
        method="GET",
        url="https://codeload.github.com/acme/landing-template/tar.gz/main",
        content=tarball,
    )

    fetcher = GithubTemplateFetcher()
    project_dir = await fetcher.fetch("acme/landing-template", "main")

    assert os.path.isfile(os.path.join(project_dir, "package.json"))
    assert os.path.isfile(os.path.join(project_dir, "src", "pages", "index.astro"))
    assert not os.path.isdir(os.path.join(project_dir, "landing-template-main"))


async def test_fetch_raises_on_http_error(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        method="GET",
        url="https://codeload.github.com/acme/missing/tar.gz/main",
        status_code=404,
    )

    fetcher = GithubTemplateFetcher()
    with pytest.raises(httpx.HTTPStatusError):
        await fetcher.fetch("acme/missing", "main")
