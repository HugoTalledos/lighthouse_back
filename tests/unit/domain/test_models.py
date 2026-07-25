import pytest
from pydantic import ValidationError
from src.agent.tools.image_builder.domain.models import (
    ImageBrief, GeneratedImage, ComposedCreative, ImageBuildResult,
)


def _valid_brief(**overrides):
    data = dict(
        project_id="proj-1",
        business_name="Acme Co",
        value_proposition="Saves you 10 hours a week",
        target_customer="Busy professionals",
        headline="Save time every day",
        cta_text="Start free trial",
        style_hints=["minimalist", "warm tones"],
        n_images=3,
    )
    data.update(overrides)
    return data


def test_brief_roundtrip():
    brief = ImageBrief.model_validate(_valid_brief())
    assert brief.business_name == "Acme Co"
    assert brief.n_images == 3


def test_brief_default_n_images():
    data = _valid_brief()
    del data["n_images"]
    brief = ImageBrief.model_validate(data)
    assert brief.n_images == 3


def test_headline_too_long():
    with pytest.raises(ValidationError, match="headline"):
        ImageBrief.model_validate(_valid_brief(headline="x" * 41))


def test_cta_too_long():
    with pytest.raises(ValidationError, match="cta_text"):
        ImageBrief.model_validate(_valid_brief(cta_text="x" * 21))


def test_result_model_dump_is_serializable():
    brief = ImageBrief.model_validate(_valid_brief())
    creative = ComposedCreative(
        variant_index=0,
        image_bytes=b"fake",
        storage_url="https://example.com/img.png",
        headline="Save time every day",
        cta_text="Start free trial",
        prompt_used="A background...",
        provider="openrouter",
    )
    result = ImageBuildResult(
        brief=brief,
        creatives=[creative],
        status="success",
        errors=[],
    )
    dumped = result.model_dump()
    assert dumped["status"] == "success"
    assert dumped["creatives"][0]["provider"] == "openrouter"
    assert isinstance(dumped["brief"]["style_hints"], list)


def test_generated_image_is_the_shared_model():
    from src.agent.tools.image_builder.domain import models as image_builder_models
    from src.shared.image_gen.domain.models import GeneratedImage as SharedGeneratedImage

    assert image_builder_models.GeneratedImage is SharedGeneratedImage
