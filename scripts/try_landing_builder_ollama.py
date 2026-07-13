"""
Script manual para probar landing_builder contra un Ollama local real para el
LLM. No es parte del pipeline de tests automatizados - solo para pruebas
manuales.

En vez de desplegar a un canal de preview de Firebase Hosting, copia el sitio
generado a scripts/output_landings/<project_id>/ y lo sirve por HTTP local
(no requiere FIREBASE_HOSTING_SITE_ID ni FIREBASE_STORAGE_BUCKET). Astro
genera rutas de assets absolutas (/_astro/...), asi que el preview debe
servirse por HTTP - abrir el HTML directo con file:// no carga bien
estilos/scripts.

Uso:
    cd /Users/hugotalledos/programacion/proyectos/light_house/lighthouse_back
    LANDING_TEMPLATE_REPO=owner/repo LLM_PROVIDER=ollama OLLAMA_MODEL=qwen2.5-coder:7b \
    python3 -m scripts.try_landing_builder_ollama

El script imprime la URL de preview (http://localhost:4321/<project_id>/ por
defecto, override con LOCAL_PREVIEW_PORT) y queda corriendo hasta Ctrl+C.
"""
from __future__ import annotations
import asyncio
import http.server
import json
import logging
import os
import shutil
import threading
from pathlib import Path

from src.shared.llm.factory import build_llm_client
from src.agent.tools.landing_builder.domain.models import LandingBrief
from src.agent.tools.landing_builder.domain.ports import HostingPort, PreviewDeployment
from src.agent.tools.landing_builder.application.landing_builder_service import LandingBuilderService
from src.agent.tools.landing_builder.infrastructure.github_template_fetcher import GithubTemplateFetcher
from src.agent.tools.landing_builder.infrastructure.astro_builder import AstroNodeBuilder

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).parent / "output_landings"
DEFAULT_PORT = 4321

MOCK_BRIEF = dict(
    project_id="proj-mock-1",
    business_name="Acme Coffee",
    value_proposition="Cafe de especialidad entregado en 24h",
    target_customer="Amantes del cafe de especialidad, 25-45 anios",
    product_or_service="Suscripcion mensual de cafe en grano",
    tone_hint="calido",
    primary_cta_goal="Suscribirse al plan mensual",
    brand_color_hint="#6F4E37",
)


class LocalHostingAdapter(HostingPort):
    """Copia dist/ a disco y lo sirve por HTTP local en vez de subirlo a Firebase Hosting - solo para pruebas manuales."""

    def __init__(self, output_dir: Path) -> None:
        self._output_dir = output_dir
        self._port = int(os.getenv("LOCAL_PREVIEW_PORT", str(DEFAULT_PORT)))
        self._server: http.server.ThreadingHTTPServer | None = None

    async def deploy_preview(self, dist_dir: str, channel_id: str) -> PreviewDeployment:
        target_dir = self._output_dir / channel_id
        target_dir.mkdir(parents=True, exist_ok=True)
        shutil.copytree(dist_dir, target_dir, dirs_exist_ok=True)

        self._ensure_server_running()

        return PreviewDeployment(
            url=f"http://localhost:{self._port}/{channel_id}/",
            expire_time=None,
        )

    def _ensure_server_running(self) -> None:
        if self._server is not None:
            return

        output_dir = str(self._output_dir)

        class _Handler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs) -> None:
                super().__init__(*args, directory=output_dir, **kwargs)

            def log_message(self, format: str, *args) -> None:
                logger.info("[preview server] " + format, *args)

        self._server = http.server.ThreadingHTTPServer(("localhost", self._port), _Handler)
        thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        thread.start()
        logger.info("Servidor de preview local escuchando en http://localhost:%d/", self._port)

    def shutdown(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server = None
