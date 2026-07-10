from __future__ import annotations
from .models import LandingBrief

_SECTION_CATALOG = (
    "- hero: headline, subheadline, optional image_url, cta_text, optional cta_url. "
    "The page's opening statement and primary call to action.\n"
    "- features: optional headline, items (3-6 of {icon, title, description}). "
    "Highlights product/service capabilities.\n"
    "- testimonials: items ({quote, author_name, optional author_role}). Social proof.\n"
    "- pricing: plans ({name, price, optional period, features, cta_text}). Pricing tiers.\n"
    "- faq: items ({question, answer}). Answers common objections.\n"
    "- cta: headline, optional subheadline, button_text, optional button_url. "
    "A closing call to action before the footer.\n"
    "- footer: business_name, links ({label, url}), social_links ({platform, url}). "
    "Always the last section.\n"
)


def build_landing_prompt(brief: LandingBrief) -> tuple[str, str]:
    system = (
        "You are an expert landing-page copywriter and conversion-rate-optimization "
        "(CRO) strategist. Your task is to compose a landing page as a structured "
        "sequence of sections, chosen only from a fixed library of section types — "
        "you never write HTML, CSS, or JavaScript directly.\n\n"
        "Available section types:\n"
        f"{_SECTION_CATALOG}\n"
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
