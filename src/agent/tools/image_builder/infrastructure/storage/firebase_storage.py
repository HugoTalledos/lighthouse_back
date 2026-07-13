from __future__ import annotations
import asyncio
import os
import firebase_admin
from firebase_admin import storage as fb_storage

from ..domain.ports import ImageStoragePort


class FirebaseStorageAdapter(ImageStoragePort):
    def __init__(self) -> None:
        bucket_name = os.getenv("FIREBASE_STORAGE_BUCKET")
        if not bucket_name:
            raise ValueError("FIREBASE_STORAGE_BUCKET environment variable is not set")
        self._bucket_name = bucket_name
        if not firebase_admin._apps:
            firebase_admin.initialize_app(options={"storageBucket": bucket_name})

    async def upload(self, image_bytes: bytes, filename: str, project_id: str) -> str:
        bucket = fb_storage.bucket(self._bucket_name)
        blob = bucket.blob(f"creatives/{project_id}/{filename}")
        await asyncio.to_thread(blob.upload_from_string, image_bytes, content_type="image/png")
        await asyncio.to_thread(blob.make_public)
        return blob.public_url
