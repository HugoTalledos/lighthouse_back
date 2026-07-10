from __future__ import annotations
import os
from src.agent.tools.landing_builder.domain.models import (
    Theme, HeroSection, FooterSection, PageComposition, LandingPromoteResult,
)
from src.agent.tools.landing_builder.domain.ports import TemplateSourcePort, LandingStoragePort
from src.agent.tools.landing_builder.application.landing_promotion_service import (
    LandingPromotionService,
)


def _composition():
    return PageComposition(
        theme=Theme(primary_color="#111", secondary_color="#eee", font_family="Inter"),
        sections=[
            HeroSection(headline="Welcome", subheadline="Sub", cta_text="Start"),
            FooterSection(business_name="Acme", links=[], social_links=[]),
        ],
    )


class FakeTemplateSource(TemplateSourcePort):
    def __init__(self, project_dir, raise_exc=None):
        self._project_dir = project_dir
        self._raise = raise_exc
        self.fetch_calls = []

    async def fetch(self, repo, ref):
        self.fetch_calls.append((repo, ref))
        if self._raise:
            raise self._raise
        return self._project_dir


class FakeStorage(LandingStoragePort):
    def __init__(self, storage_path=None, raise_exc=None):
        self._storage_path = storage_path
        self._raise = raise_exc
        self.save_calls = []
        # Captured at save_snapshot() time — the service's `finally` block
        # always removes project_dir before a test could inspect it
        # afterward, so this flag is the only reliable evidence render() ran
        # before save_snapshot().
        self.page_json_existed_at_save_time = None

    async def save_snapshot(self, project_id, version, project_dir):
        self.save_calls.append((project_id, version, project_dir))
        self.page_json_existed_at_save_time = os.path.exists(
            os.path.join(project_dir, "src", "data", "page.json")
        )
        if self._raise:
            raise self._raise
        return self._storage_path


def _service(template_source, storage):
    return LandingPromotionService(
        template_source, storage, template_repo="acme/landing-template", template_ref="main"
    )


async def test_success_path_returns_version_and_storage_path(tmp_path):
    service = _service(
        FakeTemplateSource(str(tmp_path)),
        FakeStorage(storage_path="landings/proj-1/20260710T000000Z/source.tar.gz"),
    )
    result = await service.promote("proj-1", _composition())
    assert result.status == "success"
    assert result.storage_path == "landings/proj-1/20260710T000000Z/source.tar.gz"
    assert result.version is not None
    assert result.errors == []


async def test_success_path_renders_before_saving(tmp_path):
    storage = FakeStorage(storage_path="landings/proj-1/v1/source.tar.gz")
    service = _service(
        FakeTemplateSource(str(tmp_path)), storage
    )
    await service.promote("proj-1", _composition())
    assert storage.page_json_existed_at_save_time is True


async def test_template_fetch_failure_returns_failed(tmp_path):
    service = _service(
        FakeTemplateSource(str(tmp_path), raise_exc=RuntimeError("github down")), FakeStorage()
    )
    result = await service.promote("proj-1", _composition())
    assert result.status == "failed"
    assert result.version is None
    assert "github down" in result.errors[0]


async def test_storage_failure_returns_failed(tmp_path):
    service = _service(
        FakeTemplateSource(str(tmp_path)), FakeStorage(raise_exc=RuntimeError("upload failed"))
    )
    result = await service.promote("proj-1", _composition())
    assert result.status == "failed"
    assert "upload failed" in result.errors[0]


async def test_project_dir_is_removed_after_promote(tmp_path):
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    service = _service(
        FakeTemplateSource(str(project_dir)),
        FakeStorage(storage_path="landings/proj-1/v1/source.tar.gz"),
    )
    await service.promote("proj-1", _composition())
    assert not project_dir.exists()


async def test_never_raises(tmp_path):
    service = _service(
        FakeTemplateSource(str(tmp_path), raise_exc=Exception("boom")), FakeStorage()
    )
    result = await service.promote("proj-1", _composition())
    assert isinstance(result, LandingPromoteResult)
