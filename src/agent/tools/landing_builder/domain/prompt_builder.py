from __future__ import annotations
from .models import LandingBrief


def build_landing_prompt(brief: LandingBrief, page_json_doc: str) -> tuple[str, str]:
    system = (
        "You are an expert landing-page copywriter and conversion-rate-optimization "
        "(CRO) strategist. Your task is to compose a landing page as a structured "
        "sequence of sections, chosen only from a fixed library of section types — "
        "you never write HTML, CSS, or JavaScript directly. The exact JSON shape you "
        "must produce, including every available section type and field, is documented "
        "below:\n\n"
        f"{page_json_doc}\n\n"
        "Requirements:\n"
        "- Produce a coherent section order: a hero section should conventionally "
        "come first and a footer section should conventionally come last.\n"
        "- Pick a theme (colors, font) that fits the requested tone and brand color "
        "hint when provided.\n"
        "- Copy must be concise and CTA-driven; when a primary CTA goal is provided, "
        "every call to action should work toward it.\n"
    )

    lines = [
        f"Business: {brief.business_name}",
        f"Value proposition: {brief.value_proposition}",
        f"Target customer: {brief.target_customer}",
        f"Product/Service: {brief.product_or_service}",
    ]
    if brief.tone_hint is not None:
        lines.append(f"Tone: {brief.tone_hint}")
    if brief.primary_cta_goal is not None:
        lines.append(f"Primary CTA goal: {brief.primary_cta_goal}")
    if brief.brand_color_hint is not None:
        lines.append(f"Brand color hint: {brief.brand_color_hint}")

    user = "\n".join(lines)
    return system, user
