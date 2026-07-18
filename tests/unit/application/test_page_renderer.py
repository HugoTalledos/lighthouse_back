from __future__ import annotations
from src.agent.tools.landing_builder.domain.models import (
    Theme, HeroSection, FooterSection, PageComposition,
)
from src.agent.tools.landing_builder.application.page_renderer import render


def _composition():
    return PageComposition(
        theme=Theme(primary_color="#111111", secondary_color="#eeeeee", font_family="Inter"),
        sections=[
            HeroSection(type="hero", headline="Welcome", subheadline="Sub", cta_text="Start"),
            FooterSection(type="footer", business_name="Acme", links=[], social_links=[]),
        ],
    )


def test_render_writes_page_json(tmp_path):
    render(_composition(), str(tmp_path))
    assert (tmp_path / "src" / "data" / "page.json").exists()


def test_render_writes_valid_json_round_trip(tmp_path):
    composition = _composition()
    render(composition, str(tmp_path))
    loaded = PageComposition.model_validate_json(
        (tmp_path / "src" / "data" / "page.json").read_text()
    )
    assert loaded == composition


def test_render_creates_nested_directories(tmp_path):
    render(_composition(), str(tmp_path))
    assert (tmp_path / "src" / "data").is_dir()


def test_render_is_deterministic(tmp_path):
    composition = _composition()
    render(composition, str(tmp_path / "a"))
    render(composition, str(tmp_path / "b"))
    content_a = (tmp_path / "a" / "src" / "data" / "page.json").read_text()
    content_b = (tmp_path / "b" / "src" / "data" / "page.json").read_text()
    assert content_a == content_b
