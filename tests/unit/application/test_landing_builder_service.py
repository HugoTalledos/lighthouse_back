from __future__ import annotations
import os
from src.shared.llm.domain.ports import LLMClientPort
from src.agent.tools.landing_builder.domain.models import (
    LandingBrief, Theme, HeroSection, FooterSection, PageComposition, LandingBuildResult,
)
from src.agent.tools.landing_builder.domain.ports import (
    TemplateSourcePort, StaticBuilderPort, HostingPort, BuildResult, PreviewDeployment,
)
from src.agent.tools.landing_builder.application.landing_builder_service import LandingBuilderService


def _brief(**overrides):
    defaults = dict(
        project_id="proj-1",
        business_name="Acme",
        value_proposition="Saves time",
        target_customer="Professionals",
        product_or_service="Landing pages",
    )
    return LandingBrief(**{**defaults, **overrides})


def _composition():
    return PageComposition(
        theme=Theme(primary_color="#111", secondary_color="#eee", font_family="Inter"),
        sections=[
            HeroSection(headline="Welcome", subheadline="Sub", cta_text="Start"),
            FooterSection(business_name="Acme", links=[], social_links=[]),
        ],
    )


class FakeLLMClient(LLMClientPort):
    def __init__(self, return_value=None, raise_exc=None):
        self._return = return_value
        self._raise = raise_exc

    async def complete(self, prompt, *, system=None, temperature=0.7):
        raise NotImplementedError

    async def generate_structured(self, prompt, response_type, *, system=None, temperature=0.4):
        if self._raise:
            raise self._raise
        return self._return


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


class FakeBuilder(StaticBuilderPort):
    def __init__(self, result):
        self._result = result
        # Captured at build() time — the service's `finally` block always
        # removes project_dir before this test can inspect it afterward, so
        # this flag is the only reliable evidence render() ran before build().
        self.page_json_existed_at_build_time = None

    async def build(self, project_dir):
        self.page_json_existed_at_build_time = os.path.exists(
            os.path.join(project_dir, "src", "data", "page.json")
        )
        return self._result


class FakeHosting(HostingPort):
    def __init__(self, deployment=None, raise_exc=None):
        self._deployment = deployment
        self._raise = raise_exc

    async def deploy_preview(self, dist_dir, channel_id):
        if self._raise:
            raise self._raise
        return self._deployment


def _service(tmp_path, llm=None, builder_result=None, hosting=None, builder=None):
    return LandingBuilderService(
        llm or FakeLLMClient(return_value=_composition()),
        FakeTemplateSource(str(tmp_path)),
        builder
        or FakeBuilder(
            builder_result
            or BuildResult(success=True, dist_dir=str(tmp_path / "dist"), logs="ok")
        ),
        hosting or FakeHosting(deployment=PreviewDeployment(url="https://preview.example.com", expire_time=None)),
        template_repo="acme/landing-template",
        template_ref="main",
    )


async def test_success_path_returns_preview_url(tmp_path):
    result = await _service(tmp_path).build(_brief())
    assert result.status == "success"
    assert result.preview_url == "https://preview.example.com"
    assert result.composition is not None
    assert result.errors == []


async def test_success_path_renders_page_json_before_build(tmp_path):
    builder = FakeBuilder(BuildResult(success=True, dist_dir=str(tmp_path / "dist"), logs="ok"))
    await _service(tmp_path, builder=builder).build(_brief())
    assert builder.page_json_existed_at_build_time is True


async def test_llm_failure_returns_failed_with_no_composition(tmp_path):
    service = _service(tmp_path, llm=FakeLLMClient(raise_exc=RuntimeError("LLM down")))
    result = await service.build(_brief())
    assert result.status == "failed"
    assert result.composition is None
    assert "LLM down" in result.errors[0]


async def test_build_failure_keeps_composition_and_reports_logs(tmp_path):
    builder_result = BuildResult(success=False, dist_dir=None, logs="astro build failed: syntax error")
    service = _service(tmp_path, builder_result=builder_result)
    result = await service.build(_brief())
    assert result.status == "failed"
    assert result.composition is not None
    assert "astro build failed" in result.errors[0]
    assert result.preview_url is None


async def test_deploy_failure_returns_failed(tmp_path):
    service = _service(tmp_path, hosting=FakeHosting(raise_exc=RuntimeError("deploy exploded")))
    result = await service.build(_brief())
    assert result.status == "failed"
    assert "deploy exploded" in result.errors[0]


async def test_template_fetch_failure_returns_failed_with_no_composition(tmp_path):
    service = LandingBuilderService(
        FakeLLMClient(return_value=_composition()),
        FakeTemplateSource(str(tmp_path), raise_exc=RuntimeError("github down")),
        FakeBuilder(BuildResult(success=True, dist_dir=str(tmp_path / "dist"), logs="ok")),
        FakeHosting(deployment=PreviewDeployment(url="https://x", expire_time=None)),
        template_repo="acme/landing-template",
        template_ref="main",
    )
    result = await service.build(_brief())
    assert result.status == "failed"
    assert result.composition is None
    assert "github down" in result.errors[0]


async def test_project_dir_is_removed_after_build(tmp_path):
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    service = LandingBuilderService(
        FakeLLMClient(return_value=_composition()),
        FakeTemplateSource(str(project_dir)),
        FakeBuilder(BuildResult(success=True, dist_dir=str(project_dir / "dist"), logs="ok")),
        FakeHosting(deployment=PreviewDeployment(url="https://x", expire_time=None)),
        template_repo="acme/landing-template",
        template_ref="main",
    )
    await service.build(_brief())
    assert not project_dir.exists()


async def test_never_raises(tmp_path):
    service = _service(tmp_path, llm=FakeLLMClient(raise_exc=Exception("boom")))
    result = await service.build(_brief())
    assert isinstance(result, LandingBuildResult)
