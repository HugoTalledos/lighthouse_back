from __future__ import annotations
import shutil
from datetime import datetime

from ..domain.models import PageComposition, LandingPromoteResult
from ..domain.ports import TemplateSourcePort, LandingStoragePort
from .page_renderer import render


class LandingPromotionService:
    def __init__(
        self,
        template_source: TemplateSourcePort,
        storage: LandingStoragePort,
        template_repo: str,
        template_ref: str = "main",
    ) -> None:
        self._template_source = template_source
        self._storage = storage
        self._template_repo = template_repo
        self._template_ref = template_ref

    async def promote(self, project_id: str, composition: PageComposition) -> LandingPromoteResult:
        project_dir = None
        try:
            project_dir = await self._template_source.fetch(self._template_repo, self._template_ref)
            render(composition, project_dir)
            version = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
            storage_path = await self._storage.save_snapshot(project_id, version, project_dir)
            return LandingPromoteResult(
                project_id=project_id, version=version, storage_path=storage_path,
                status="success", errors=[],
            )
        except Exception as e:
            return LandingPromoteResult(
                project_id=project_id, version=None, storage_path=None,
                status="failed", errors=[str(e)],
            )
        finally:
            if project_dir:
                shutil.rmtree(project_dir, ignore_errors=True)
