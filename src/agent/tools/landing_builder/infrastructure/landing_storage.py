from __future__ import annotations
import asyncio
import io
import os
import tarfile
import firebase_admin
from firebase_admin import storage as fb_storage

from ..domain.ports import LandingStoragePort

_EXCLUDED = {"node_modules", ".git", "dist"}


class FirebaseLandingStorage(LandingStoragePort):
    def __init__(self) -> None:
        bucket_name = os.getenv("FIREBASE_STORAGE_BUCKET")
        if not bucket_name:
            raise ValueError("FIREBASE_STORAGE_BUCKET environment variable is not set")
        self._bucket_name = bucket_name
        if not firebase_admin._apps:
            firebase_admin.initialize_app(options={"storageBucket": bucket_name})

    async def save_snapshot(self, project_id: str, version: str, project_dir: str) -> str:
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
            for entry in sorted(os.listdir(project_dir)):
                if entry in _EXCLUDED:
                    continue
                tar.add(os.path.join(project_dir, entry), arcname=entry)
        buffer.seek(0)

        storage_path = f"landings/{project_id}/{version}/source.tar.gz"
        bucket = fb_storage.bucket(self._bucket_name)
        blob = bucket.blob(storage_path)
        await asyncio.to_thread(
            blob.upload_from_string, buffer.getvalue(), content_type="application/gzip"
        )
        return storage_path
