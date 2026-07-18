from __future__ import annotations
from typing import Annotated, Literal, Union
from pydantic import BaseModel, Field


class LandingBrief(BaseModel):
    project_id: str
    business_name: str
    value_proposition: str
    target_customer: str
    product_or_service: str
    tone_hint: str | None = None
    primary_cta_goal: str | None = None
    brand_color_hint: str | None = None


class Theme(BaseModel):
    primary_color: str
    secondary_color: str
    font_family: str
    logo_url: str | None = None
    logo_text: str | None = None
    logo_icon: str | None = None


class FeatureItem(BaseModel):
    icon: str
    title: str
    description: str


class Testimonial(BaseModel):
    quote: str
    author_name: str
    author_role: str | None = None


class PricingPlan(BaseModel):
    name: str
    price: str
    period: str | None = None
    features: list[str]
    cta_text: str


class FAQItem(BaseModel):
    question: str
    answer: str


class FooterLink(BaseModel):
    label: str
    url: str


class SocialLink(BaseModel):
    platform: str
    url: str


class HeroSection(BaseModel):
    type: Literal["hero"]
    headline: str
    subheadline: str
    image_url: str | None = None
    cta_text: str
    cta_url: str | None = None


class FeaturesSection(BaseModel):
    type: Literal["features"]
    headline: str | None = None
    items: list[FeatureItem] = Field(min_length=3, max_length=6)


class TestimonialsSection(BaseModel):
    type: Literal["testimonials"]
    items: list[Testimonial]


class PricingSection(BaseModel):
    type: Literal["pricing"]
    plans: list[PricingPlan]


class FAQSection(BaseModel):
    type: Literal["faq"]
    items: list[FAQItem]


class CTASection(BaseModel):
    type: Literal["cta"]
    headline: str
    subheadline: str | None = None
    button_text: str
    button_url: str | None = None


class FooterSection(BaseModel):
    type: Literal["footer"]
    business_name: str
    links: list[FooterLink]
    social_links: list[SocialLink]


Section = Annotated[
    Union[
        HeroSection,
        FeaturesSection,
        TestimonialsSection,
        PricingSection,
        FAQSection,
        CTASection,
        FooterSection,
    ],
    Field(discriminator="type"),
]


class PageComposition(BaseModel):
    theme: Theme
    sections: list[Section] = Field(min_length=1)


class LandingBuildResult(BaseModel):
    brief: LandingBrief
    composition: PageComposition | None
    preview_url: str | None
    status: Literal["success", "failed"]
    errors: list[str]


class LandingPromoteResult(BaseModel):
    project_id: str
    version: str | None
    storage_path: str | None
    status: Literal["success", "failed"]
    errors: list[str]
