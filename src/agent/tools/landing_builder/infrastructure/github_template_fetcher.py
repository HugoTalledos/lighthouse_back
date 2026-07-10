from __future__ import annotations
import io
import os
import shutil
import tarfile
import tempfile
import httpx

from ..domain.ports import TemplateSourcePort

_TIMEOUT = 60.0


class GithubTemplateFetcher(TemplateSourcePort):
    async def fetch(self, repo: str, ref: str) -> str:
        url = f"https://codeload.github.com/{repo}/tar.gz/{ref}"
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.get(url)
            response.raise_for_status()

        extract_dir = tempfile.mkdtemp(prefix="landing-template-raw-")
        with tarfile.open(fileobj=io.BytesIO(response.content), mode="r:gz") as tar:
            tar.extractall(extract_dir)

        entries = os.listdir(extract_dir)
        if len(entries) != 1:
            raise ValueError(f"Unexpected template archive layout: {entries}")

        project_dir = tempfile.mkdtemp(prefix="landing-template-")
        os.rmdir(project_dir)
        shutil.move(os.path.join(extract_dir, entries[0]), project_dir)
        shutil.rmtree(extract_dir, ignore_errors=True)
        return project_dir
