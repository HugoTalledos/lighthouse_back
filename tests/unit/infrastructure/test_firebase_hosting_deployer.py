from __future__ import annotations
import gzip
import hashlib
from unittest.mock import MagicMock, patch
import pytest
from pytest_httpx import HTTPXMock
from src.agent.tools.landing_builder.infrastructure.firebase_hosting_deployer import (
    FirebaseHostingDeployer,
)


def _fake_credentials(token: str):
    creds = MagicMock()
    creds.token = token
    creds.refresh = MagicMock()
    return creds


def test_missing_site_id_raises(monkeypatch):
    monkeypatch.delenv("FIREBASE_HOSTING_SITE_ID", raising=False)
    with pytest.raises(ValueError, match="FIREBASE_HOSTING_SITE_ID"):
        FirebaseHostingDeployer()


async def test_deploy_preview_full_flow(monkeypatch, tmp_path, httpx_mock: HTTPXMock):
    monkeypatch.setenv("FIREBASE_HOSTING_SITE_ID", "my-site")

    (tmp_path / "index.html").write_text("<html></html>")
    compressed = gzip.compress(b"<html></html>")
    file_hash = hashlib.sha256(compressed).hexdigest()
    version_name = "sites/my-site/versions/v1"

    httpx_mock.add_response(
        method="POST",
        url="https://firebasehosting.googleapis.com/v1beta1/sites/my-site/channels?channelId=proj-1",
        json={"name": "sites/my-site/channels/proj-1"},
    )
    httpx_mock.add_response(
        method="POST",
        url="https://firebasehosting.googleapis.com/v1beta1/sites/my-site/versions",
        json={"name": version_name},
    )
    httpx_mock.add_response(
        method="POST",
        url=f"https://firebasehosting.googleapis.com/v1beta1/{version_name}:populateFiles",
        json={"uploadUrl": "https://upload.example.com/upload", "uploadRequiredHashes": [file_hash]},
    )
    httpx_mock.add_response(
        method="POST",
        url=f"https://upload.example.com/upload/{file_hash}",
        json={},
    )
    httpx_mock.add_response(
        method="PATCH",
        url=f"https://firebasehosting.googleapis.com/v1beta1/{version_name}?updateMask=status",
        json={"status": "FINALIZED"},
    )
    httpx_mock.add_response(
        method="POST",
        url=(
            "https://firebasehosting.googleapis.com/v1beta1/sites/my-site/"
            f"channels/proj-1/releases?versionName={version_name}"
        ),
        json={"name": "sites/my-site/channels/proj-1/releases/1"},
    )
    httpx_mock.add_response(
        method="GET",
        url="https://firebasehosting.googleapis.com/v1beta1/sites/my-site/channels/proj-1",
        json={"url": "https://proj-1--my-site.web.app", "expireTime": "2026-07-17T00:00:00Z"},
    )

    with patch("google.auth.default", return_value=(_fake_credentials("fake-token"), "proj")), \
         patch("google.auth.transport.requests.Request", return_value=MagicMock()):
        deployer = FirebaseHostingDeployer()
        result = await deployer.deploy_preview(str(tmp_path), channel_id="proj-1")

    assert result.url == "https://proj-1--my-site.web.app"
    assert result.expire_time == "2026-07-17T00:00:00Z"


async def test_deploy_preview_ignores_channel_already_exists(monkeypatch, tmp_path, httpx_mock: HTTPXMock):
    monkeypatch.setenv("FIREBASE_HOSTING_SITE_ID", "my-site")
    (tmp_path / "index.html").write_text("<html></html>")
    compressed = gzip.compress(b"<html></html>")
    file_hash = hashlib.sha256(compressed).hexdigest()
    version_name = "sites/my-site/versions/v1"

    httpx_mock.add_response(
        method="POST",
        url="https://firebasehosting.googleapis.com/v1beta1/sites/my-site/channels?channelId=proj-1",
        status_code=409,
    )
    httpx_mock.add_response(
        method="POST",
        url="https://firebasehosting.googleapis.com/v1beta1/sites/my-site/versions",
        json={"name": version_name},
    )
    httpx_mock.add_response(
        method="POST",
        url=f"https://firebasehosting.googleapis.com/v1beta1/{version_name}:populateFiles",
        json={"uploadUrl": "https://upload.example.com/upload", "uploadRequiredHashes": [file_hash]},
    )
    httpx_mock.add_response(
        method="POST",
        url=f"https://upload.example.com/upload/{file_hash}",
        json={},
    )
    httpx_mock.add_response(
        method="PATCH",
        url=f"https://firebasehosting.googleapis.com/v1beta1/{version_name}?updateMask=status",
        json={"status": "FINALIZED"},
    )
    httpx_mock.add_response(
        method="POST",
        url=(
            "https://firebasehosting.googleapis.com/v1beta1/sites/my-site/"
            f"channels/proj-1/releases?versionName={version_name}"
        ),
        json={"name": "sites/my-site/channels/proj-1/releases/1"},
    )
    httpx_mock.add_response(
        method="GET",
        url="https://firebasehosting.googleapis.com/v1beta1/sites/my-site/channels/proj-1",
        json={"url": "https://proj-1--my-site.web.app"},
    )

    with patch("google.auth.default", return_value=(_fake_credentials("fake-token"), "proj")), \
         patch("google.auth.transport.requests.Request", return_value=MagicMock()):
        deployer = FirebaseHostingDeployer()
        result = await deployer.deploy_preview(str(tmp_path), channel_id="proj-1")

    assert result.url == "https://proj-1--my-site.web.app"
