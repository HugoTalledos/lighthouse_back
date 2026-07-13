from __future__ import annotations
import io
import pytest
from PIL import Image
from src.agent.tools.image_builder.domain.models import ImageBrief, GeneratedImage
from src.agent.tools.image_builder.infrastructure.pillow_composer import PillowImageComposer


def _make_png_bytes(width=1792, height=1024) -> bytes:
    img = Image.new("RGB", (width, height), color=(200, 100, 50))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _brief():
    return ImageBrief(
        project_id="p1",
        business_name="Acme",
        value_proposition="Saves time",
        target_customer="Professionals",
        headline="Save time every day",
        cta_text="Start free trial",
        style_hints=["clean"],
        n_images=1,
    )


def _fake_image(png_bytes: bytes) -> GeneratedImage:
    return GeneratedImage(
        provider="dalle3",
        image_bytes=png_bytes,
        prompt_used="prompt",
        width=1792,
        height=1024,
    )


def test_compose_returns_png_bytes():
    composer = PillowImageComposer()
    result = composer.compose(_fake_image(_make_png_bytes()), _brief())
    assert result[:8] == b"\x89PNG\r\n\x1a\n"


def test_compose_output_dimensions():
    composer = PillowImageComposer()
    result = composer.compose(_fake_image(_make_png_bytes()), _brief())
    img = Image.open(io.BytesIO(result))
    assert img.size == (1200, 628)


def test_compose_accepts_smaller_source_image():
    composer = PillowImageComposer()
    # 800x600 source — must be upscaled and cropped to 1200x628
    result = composer.compose(_fake_image(_make_png_bytes(800, 600)), _brief())
    img = Image.open(io.BytesIO(result))
    assert img.size == (1200, 628)
