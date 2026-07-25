import pytest
from src.agent.tools.image_builder.domain.models import (
    ImageBrief, GeneratedImage, ComposedCreative, ImageBuildResult,
)
from src.agent.tools.image_builder.domain.ports import (
    ImageGeneratorPort, ImageComposerPort, ImageStoragePort,
)
from src.agent.tools.image_builder.application.image_builder_service import ImageBuilderService


def _brief(n_images=2):
    return ImageBrief(
        project_id="proj-abc",
        business_name="My Business",
        value_proposition="Saves time",
        target_customer="Professionals",
        headline="Save Time Now",
        cta_text="Get Started",
        style_hints=["clean"],
        n_images=n_images,
    )


def _fake_image(i=0):
    return GeneratedImage(
        provider="openrouter",
        image_bytes=b"fake-image-bytes",
        prompt_used=f"prompt {i}",
        width=1792,
        height=1024,
    )


class StubGenerator(ImageGeneratorPort):
    def __init__(self, side_effects):
        self._effects = iter(side_effects)

    async def generate(self, prompt, width, height):
        effect = next(self._effects)
        if isinstance(effect, Exception):
            raise effect
        return effect


class StubComposer(ImageComposerPort):
    def compose(self, image, brief):
        return b"composed-png-bytes"


class StubStorage(ImageStoragePort):
    async def upload(self, image_bytes, filename, project_id):
        return f"https://storage.example.com/{project_id}/{filename}"


async def test_all_succeed_returns_success():
    brief = _brief(n_images=2)
    service = ImageBuilderService(
        generator=StubGenerator([_fake_image(0), _fake_image(1)]),
        composer=StubComposer(),
        storage=StubStorage(),
    )
    result = await service.build(brief)
    assert result.status == "success"
    assert len(result.creatives) == 2
    assert result.errors == []


async def test_one_failure_returns_partial():
    brief = _brief(n_images=2)
    service = ImageBuilderService(
        generator=StubGenerator([RuntimeError("API down"), _fake_image(1)]),
        composer=StubComposer(),
        storage=StubStorage(),
    )
    result = await service.build(brief)
    assert result.status == "partial"
    assert len(result.creatives) == 1
    assert len(result.errors) == 1
    assert "Variant 0" in result.errors[0]


async def test_all_fail_returns_failed():
    brief = _brief(n_images=2)
    service = ImageBuilderService(
        generator=StubGenerator([RuntimeError("err"), RuntimeError("err")]),
        composer=StubComposer(),
        storage=StubStorage(),
    )
    result = await service.build(brief)
    assert result.status == "failed"
    assert len(result.creatives) == 0


async def test_creative_fields_populated():
    brief = _brief(n_images=1)
    service = ImageBuilderService(
        generator=StubGenerator([_fake_image(0)]),
        composer=StubComposer(),
        storage=StubStorage(),
    )
    result = await service.build(brief)
    creative = result.creatives[0]
    assert creative.variant_index == 0
    assert creative.headline == brief.headline
    assert creative.cta_text == brief.cta_text
    assert creative.provider == "openrouter"
    assert creative.storage_url.startswith("https://")


async def test_filename_contains_slugified_business_name():
    captured_filenames = []

    class CapturingStorage(ImageStoragePort):
        async def upload(self, image_bytes, filename, project_id):
            captured_filenames.append(filename)
            return f"https://example.com/{filename}"

    brief = _brief(n_images=1)
    service = ImageBuilderService(
        generator=StubGenerator([_fake_image(0)]),
        composer=StubComposer(),
        storage=CapturingStorage(),
    )
    await service.build(brief)
    assert captured_filenames[0].startswith("my-business_0_")
    assert captured_filenames[0].endswith(".png")
