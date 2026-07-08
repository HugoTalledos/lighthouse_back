from src.agent.image_builder.domain.models import ImageBrief
from src.agent.image_builder.domain.prompt_builder import PromptBuilder


def _brief(n_images=3):
    return ImageBrief(
        project_id="p1",
        business_name="Acme",
        value_proposition="Saves 10 hours a week",
        target_customer="Busy professionals",
        headline="Save time",
        cta_text="Try free",
        style_hints=["minimalist", "warm tones"],
        n_images=n_images,
    )


def test_returns_n_prompts():
    prompts = PromptBuilder().build_prompts(_brief(n_images=3))
    assert len(prompts) == 3


def test_each_prompt_contains_value_proposition():
    prompts = PromptBuilder().build_prompts(_brief())
    for p in prompts:
        assert "Saves 10 hours a week" in p


def test_each_prompt_contains_target_customer():
    prompts = PromptBuilder().build_prompts(_brief())
    for p in prompts:
        assert "Busy professionals" in p


def test_moods_cycle_for_more_than_3_variants():
    prompts = PromptBuilder().build_prompts(_brief(n_images=5))
    assert len(prompts) == 5
    assert "warm morning light" in prompts[0]
    assert "warm morning light" in prompts[3]


def test_negative_prompt_always_present():
    prompts = PromptBuilder().build_prompts(_brief())
    for p in prompts:
        assert "no text" in p.lower()
        assert "no watermarks" in p.lower()
