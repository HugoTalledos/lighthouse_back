from __future__ import annotations
from typing import Tuple
from .models import CampaignBrief


def build_campaign_prompt(brief: CampaignBrief) -> Tuple[str, str]:
    system = (
        "You are an expert Meta Ads strategist. Your task is to produce a complete Facebook "
        "Marketing API campaign configuration from a business brief.\n\n"
        "Requirements:\n"
        "- Generate exactly one Campaign with exactly one AdSet and 1-2 Ads.\n"
        "- status must always be \"PAUSED\".\n"
        "- age_min and age_max must each be between 13 and 65; age_max must be >= age_min.\n"
        "- daily_budget_usd must be > 0 (Facebook minimum is ~1 USD/day).\n"
        "- duration_days must be > 0.\n"
        "- ads list must have at least 1 Ad; headline must be 40 characters or fewer.\n"
        "- publisher_platforms must be a subset of: facebook, instagram, audience_network, messenger.\n"
        "- Pick CampaignObjective from: OUTCOME_AWARENESS, OUTCOME_TRAFFIC, OUTCOME_ENGAGEMENT, "
        "OUTCOME_LEADS, OUTCOME_APP_PROMOTION, OUTCOME_SALES.\n"
        "- Pick OptimizationGoal from: REACH, IMPRESSIONS, LINK_CLICKS, LANDING_PAGE_VIEWS, "
        "POST_ENGAGEMENT, LEAD_GENERATION, OFFSITE_CONVERSIONS, VALUE.\n"
        "- Pick BillingEvent from: IMPRESSIONS, LINK_CLICKS.\n"
        "- Pick CallToAction from: LEARN_MORE, SHOP_NOW, SIGN_UP, SUBSCRIBE, BOOK_TRAVEL, "
        "CONTACT_US, DOWNLOAD, GET_OFFER, GET_QUOTE.\n"
    )

    lines = [
        f"Business: {brief.business_name}",
        f"Value proposition: {brief.value_proposition}",
        f"Target customer: {brief.target_customer}",
        f"Product/Service: {brief.product_or_service}",
    ]
    if brief.approx_daily_budget_usd is not None:
        lines.append(f"Approximate daily budget (USD): {brief.approx_daily_budget_usd}")
    if brief.country is not None:
        lines.append(f"Target country (ISO-2): {brief.country}")
    if brief.goal_hint is not None:
        lines.append(f"Desired outcome: {brief.goal_hint}")

    user = "\n".join(lines)
    return system, user
