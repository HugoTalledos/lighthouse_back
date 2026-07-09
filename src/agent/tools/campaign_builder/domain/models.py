from __future__ import annotations
from enum import Enum
from typing import Literal, Optional
from pydantic import BaseModel, field_validator, model_validator, Field


class CampaignObjective(str, Enum):
    OUTCOME_AWARENESS = "OUTCOME_AWARENESS"
    OUTCOME_TRAFFIC = "OUTCOME_TRAFFIC"
    OUTCOME_ENGAGEMENT = "OUTCOME_ENGAGEMENT"
    OUTCOME_LEADS = "OUTCOME_LEADS"
    OUTCOME_APP_PROMOTION = "OUTCOME_APP_PROMOTION"
    OUTCOME_SALES = "OUTCOME_SALES"


class OptimizationGoal(str, Enum):
    REACH = "REACH"
    IMPRESSIONS = "IMPRESSIONS"
    LINK_CLICKS = "LINK_CLICKS"
    LANDING_PAGE_VIEWS = "LANDING_PAGE_VIEWS"
    POST_ENGAGEMENT = "POST_ENGAGEMENT"
    LEAD_GENERATION = "LEAD_GENERATION"
    OFFSITE_CONVERSIONS = "OFFSITE_CONVERSIONS"
    VALUE = "VALUE"


class BillingEvent(str, Enum):
    IMPRESSIONS = "IMPRESSIONS"
    LINK_CLICKS = "LINK_CLICKS"


class CallToAction(str, Enum):
    LEARN_MORE = "LEARN_MORE"
    SHOP_NOW = "SHOP_NOW"
    SIGN_UP = "SIGN_UP"
    SUBSCRIBE = "SUBSCRIBE"
    BOOK_TRAVEL = "BOOK_TRAVEL"
    CONTACT_US = "CONTACT_US"
    DOWNLOAD = "DOWNLOAD"
    GET_OFFER = "GET_OFFER"
    GET_QUOTE = "GET_QUOTE"


class Gender(str, Enum):
    ALL = "ALL"
    MALE = "MALE"
    FEMALE = "FEMALE"


class CampaignBrief(BaseModel):
    project_id: str
    business_name: str
    value_proposition: str
    target_customer: str
    product_or_service: str
    approx_daily_budget_usd: Optional[float] = None
    country: Optional[str] = None
    goal_hint: Optional[str] = None


class Targeting(BaseModel):
    countries: list[str] = Field(min_length=1)
    age_min: int
    age_max: int
    genders: list[Gender] = Field(default_factory=lambda: [Gender.ALL])
    interests: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def age_max_gte_age_min(self) -> Targeting:
        if self.age_max < self.age_min:
            raise ValueError(
                f"age_max ({self.age_max}) must be >= age_min ({self.age_min})"
            )
        return self


class Placements(BaseModel):
    publisher_platforms: list[str]
    facebook_positions: Optional[list[str]] = None
    instagram_positions: Optional[list[str]] = None


class AdCreativeCopy(BaseModel):
    primary_text: str
    headline: str
    description: Optional[str] = None
    call_to_action: CallToAction
    link_url: Optional[str] = None

    @field_validator("headline")
    @classmethod
    def headline_max_40(cls, v: str) -> str:
        if len(v) > 40:
            raise ValueError("headline must be ≤ 40 characters")
        return v


class Ad(BaseModel):
    name: str
    creative: AdCreativeCopy


class AdSet(BaseModel):
    name: str
    daily_budget_usd: float = Field(gt=0)
    billing_event: BillingEvent
    optimization_goal: OptimizationGoal
    targeting: Targeting
    placements: Placements
    duration_days: int = Field(gt=0)
    ads: list[Ad] = Field(min_length=1)


class Campaign(BaseModel):
    name: str
    objective: CampaignObjective
    status: Literal["PAUSED", "ACTIVE"] = "PAUSED"
    special_ad_categories: list[str] = Field(default_factory=list)
    ad_sets: list[AdSet] = Field(min_length=1)


class CampaignConfigResult(BaseModel):
    brief: CampaignBrief
    campaign: Optional[Campaign]
    status: Literal["success", "failed"]
    errors: list[str]
