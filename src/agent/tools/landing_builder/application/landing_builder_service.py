from __future__ import annotations
import json
import shutil
import jsonschema

from src.shared.llm.domain.ports import LLMClientPort
from ..domain.models import LandingBrief, LandingBuildResult
from ..domain.ports import TemplateSourcePort, StaticBuilderPort, HostingPort
from ..domain.prompt_builder import build_landing_prompt
from .agent_docs import read_page_json_doc, read_page_schema
from .page_renderer import render


class LandingBuilderService:
    def __init__(
        self,
        llm: LLMClientPort,
        template_source: TemplateSourcePort,
        builder: StaticBuilderPort,
        hosting: HostingPort,
        template_repo: str,
        template_ref: str = "main",
    ) -> None:
        self._llm = llm
        self._template_source = template_source
        self._builder = builder
        self._hosting = hosting
        self._template_repo = template_repo
        self._template_ref = template_ref

    async def build(self, brief: LandingBrief) -> LandingBuildResult:
        project_dir = None
        composition = None
        try:
            project_dir = await self._template_source.fetch(self._template_repo, self._template_ref)
            page_json_doc = read_page_json_doc(project_dir)
            schema = read_page_schema(project_dir)
            system, user = build_landing_prompt(brief, page_json_doc)
            print("=== [DEBUG] JSON de entrada (brief) ===")
            print(json.dumps(brief.model_dump(mode="json"), indent=2, ensure_ascii=False))
            composition = await self._llm.generate_structured_from_schema(user, schema, system=system)
            jsonschema.validate(instance=composition, schema=schema)
            composition["theme"]["logo_text"] = brief.business_name
            print("=== [DEBUG] JSON decidido por el modelo (composition) ===")
            print(json.dumps(composition, indent=2, ensure_ascii=False))
            render(composition, project_dir)

            build_result = await self._builder.build(project_dir)
            if not build_result.success:
                return LandingBuildResult(
                    brief=brief, composition=composition, preview_url=None,
                    status="failed", errors=[build_result.logs],
                )

            preview = await self._hosting.deploy_preview(build_result.dist_dir, channel_id=brief.project_id)
            return LandingBuildResult(
                brief=brief, composition=composition, preview_url=preview.url,
                status="success", errors=[],
            )
        except Exception as e:
            return LandingBuildResult(
                brief=brief, composition=composition, preview_url=None,
                status="failed", errors=[str(e)],
            )
        finally:
            if project_dir:
                shutil.rmtree(project_dir, ignore_errors=True)
