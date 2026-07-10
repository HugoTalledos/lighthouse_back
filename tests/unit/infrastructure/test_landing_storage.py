from __future__ import annotations
import io
import tarfile
from unittest.mock import MagicMock, patch
import pytest
from src.agent.tools.landing_builder.infrastructure.landing_storage import FirebaseLandingStorage


def test_missing_bucket_raises(monkeypatch):
    monkeypatch.delenv("FIREBASE_STORAGE_BUCKET", raising=False)
    with pytest.raises(ValueError, match="FIREBASE_STORAGE_BUCKET"):
        FirebaseLandingStorage()


async def test_save_snapshot_excludes_node_modules_git_dist(monkeypatch, tmp_path):
    monkeypatch.setenv("FIREBASE_STORAGE_BUCKET", "my-project.appspot.com")

    (tmp_path / "package.json").write_text("{}")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "page.astro").write_text("<div/>")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "dep.js").write_text("//dep")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "HEAD").write_text("ref: refs/heads/main")
    (tmp_path / "dist").mkdir()
    (tmp_path / "dist" / "index.html").write_text("<html/>")

    fake_blob = MagicMock()
    fake_bucket = MagicMock()
    fake_bucket.blob.return_value = fake_blob

    with patch(
        "src.agent.tools.landing_builder.infrastructure.landing_storage.firebase_admin"
    ) as mock_admin, patch(
        "src.agent.tools.landing_builder.infrastructure.landing_storage.fb_storage"
    ) as mock_storage:
        mock_admin._apps = {"[DEFAULT]": True}
        mock_storage.bucket.return_value = fake_bucket

        storage = FirebaseLandingStorage()
        storage_path = await storage.save_snapshot("proj-1", "20260710T000000Z", str(tmp_path))

    assert storage_path == "landings/proj-1/20260710T000000Z/source.tar.gz"
    fake_bucket.blob.assert_called_once_with(storage_path)

    args, kwargs = fake_blob.upload_from_string.call_args
    uploaded_bytes = args[0]
    assert kwargs["content_type"] == "application/gzip"

    with tarfile.open(fileobj=io.BytesIO(uploaded_bytes), mode="r:gz") as tar:
        names = tar.getnames()

    assert "package.json" in names
    assert any(name.startswith("src") for name in names)
    assert not any(name.startswith("node_modules") for name in names)
    assert not any(name.startswith(".git") for name in names)
    assert not any(name.startswith("dist") for name in names)
