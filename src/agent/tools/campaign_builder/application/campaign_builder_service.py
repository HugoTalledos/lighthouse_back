from __future__ import annotations
import logging
from src.shared.llm.domain.ports import LLMClientPort
from ..domain.models import CampaignBrief, Campaign, CampaignConfigResult
from ..domain.prompt_builder import build_campaign_prompt

logger = logging.getLogger(__name__)


class CampaignBuilderService:
    def __init__(self, llm: LLMClientPort) -> None:
        self._llm = llm

    async def build(self, brief: CampaignBrief) -> CampaignConfigResult:
        system, user = build_campaign_prompt(brief)
        try:
            campaign = await self._llm.generate_structured(user, Campaign, system=system)
            return CampaignConfigResult(
                brief=brief,
                campaign=campaign,
                status="success",
                errors=[]
            )
        except Exception as e:
            logger.exception(
                "campaign_builder_service failed to generate campaign for project_id=%s",
                brief.project_id,
            )
            message = str(e) or type(e).__name__
            return CampaignConfigResult(
                brief=brief,
                campaign=None,
                status="failed",
                errors=[message],
            )
