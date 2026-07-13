import pytest
from unittest.mock import MagicMock, patch
from src.agent.tools.image_builder.infrastructure.storage.firebase_storage import FirebaseStorageAdapter


def test_missing_bucket_raises(monkeypatch):
    monkeypatch.delenv("FIREBASE_STORAGE_BUCKET", raising=False)
    with pytest.raises(ValueError, match="FIREBASE_STORAGE_BUCKET"):
        FirebaseStorageAdapter()


async def test_upload_calls_make_public_and_returns_url(monkeypatch):
    monkeypatch.setenv("FIREBASE_STORAGE_BUCKET", "my-project.appspot.com")

    fake_blob = MagicMock()
    fake_blob.public_url = "https://storage.googleapis.com/my-project.appspot.com/creatives/proj-1/img.png"

    fake_bucket = MagicMock()
    fake_bucket.blob.return_value = fake_blob

    with patch("src.agent.tools.image_builder.infrastructure.storage.firebase_storage.firebase_admin") as mock_admin, \
         patch("src.agent.tools.image_builder.infrastructure.storage.firebase_storage.fb_storage") as mock_storage:
        mock_admin._apps = {"[DEFAULT]": True}
        mock_storage.bucket.return_value = fake_bucket

        adapter = FirebaseStorageAdapter()
        url = await adapter.upload(b"png-bytes", "img.png", "proj-1")

    fake_bucket.blob.assert_called_once_with("creatives/proj-1/img.png")
    fake_blob.upload_from_string.assert_called_once_with(b"png-bytes", content_type="image/png")
    fake_blob.make_public.assert_called_once()
    assert url == "https://storage.googleapis.com/my-project.appspot.com/creatives/proj-1/img.png"
