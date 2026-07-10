from __future__ import annotations
import asyncio
import gzip
import hashlib
import os
from pathlib import Path

import google.auth
import google.auth.transport.requests
import httpx

from ..domain.ports import HostingPort, PreviewDeployment

_HOSTING_API = "https://firebasehosting.googleapis.com/v1beta1"
_SCOPES = ["https://www.googleapis.com/auth/firebase.hosting"]
_TIMEOUT = 60.0


class FirebaseHostingDeployer(HostingPort):
    def __init__(self) -> None:
        site_id = os.getenv("FIREBASE_HOSTING_SITE_ID")
        if not site_id:
            raise ValueError("FIREBASE_HOSTING_SITE_ID environment variable is not set")
        self._site_id = site_id

    async def _auth_headers(self) -> dict[str, str]:
        def _fetch_token() -> str:
            credentials, _ = google.auth.default(scopes=_SCOPES)
            credentials.refresh(google.auth.transport.requests.Request())
            return credentials.token

        token = await asyncio.to_thread(_fetch_token)
        return {"Authorization": f"Bearer {token}"}

    async def deploy_preview(self, dist_dir: str, channel_id: str) -> PreviewDeployment:
        headers = await self._auth_headers()

        async with httpx.AsyncClient(timeout=_TIMEOUT, headers=headers) as client:
            create_channel = await client.post(
                f"{_HOSTING_API}/sites/{self._site_id}/channels?channelId={channel_id}"
            )
            if create_channel.status_code != 409:
                create_channel.raise_for_status()

            create_version = await client.post(f"{_HOSTING_API}/sites/{self._site_id}/versions")
            create_version.raise_for_status()
            version_name = create_version.json()["name"]

            file_hashes, compressed_by_hash = self._hash_files(dist_dir)
            populate = await client.post(
                f"{_HOSTING_API}/{version_name}:populateFiles",
                json={"files": file_hashes},
            )
            populate.raise_for_status()
            populate_data = populate.json()
            upload_url = populate_data["uploadUrl"]
            required_hashes = set(populate_data.get("uploadRequiredHashes", []))

            for file_hash in required_hashes:
                upload = await client.post(
                    f"{upload_url}/{file_hash}",
                    content=compressed_by_hash[file_hash],
                    headers={"Content-Type": "application/octet-stream"},
                )
                upload.raise_for_status()

            finalize = await client.patch(
                f"{_HOSTING_API}/{version_name}?updateMask=status",
                json={"status": "FINALIZED"},
            )
            finalize.raise_for_status()

            release = await client.post(
                f"{_HOSTING_API}/sites/{self._site_id}/channels/{channel_id}/releases"
                f"?versionName={version_name}"
            )
            release.raise_for_status()
            release_data = release.json()

        return PreviewDeployment(
            url=release_data["url"],
            expire_time=release_data.get("expireTime"),
        )

    def _hash_files(self, dist_dir: str) -> tuple[dict[str, str], dict[str, bytes]]:
        file_hashes: dict[str, str] = {}
        compressed_by_hash: dict[str, bytes] = {}
        for path in Path(dist_dir).rglob("*"):
            if not path.is_file():
                continue
            rel_path = "/" + path.relative_to(dist_dir).as_posix()
            compressed = gzip.compress(path.read_bytes())
            file_hash = hashlib.sha256(compressed).hexdigest()
            file_hashes[rel_path] = file_hash
            compressed_by_hash[file_hash] = compressed
        return file_hashes, compressed_by_hash
