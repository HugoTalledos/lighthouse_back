from __future__ import annotations
import asyncio
import os

from ..domain.ports import StaticBuilderPort, BuildResult

_DEFAULT_TIMEOUT_SECONDS = 180.0


class AstroNodeBuilder(StaticBuilderPort):
    async def build(self, project_dir: str) -> BuildResult:
        timeout = float(os.getenv("LANDING_BUILD_TIMEOUT_SECONDS", str(_DEFAULT_TIMEOUT_SECONDS)))

        install_code, install_logs = await self._run(["npm", "install"], project_dir, timeout)
        if install_code is None:
            return BuildResult(
                success=False, dist_dir=None,
                logs=f"{install_logs}\nTimed out running: npm install",
            )
        if install_code != 0:
            return BuildResult(success=False, dist_dir=None, logs=install_logs)

        build_code, build_logs = await self._run(["npx", "astro", "build"], project_dir, timeout)
        combined_logs = f"{install_logs}\n{build_logs}"
        if build_code is None:
            return BuildResult(
                success=False, dist_dir=None,
                logs=f"{combined_logs}\nTimed out running: npx astro build",
            )
        if build_code != 0:
            return BuildResult(success=False, dist_dir=None, logs=combined_logs)

        return BuildResult(
            success=True, dist_dir=os.path.join(project_dir, "dist"), logs=combined_logs
        )

    async def _run(self, cmd: list[str], cwd: str, timeout: float) -> tuple[int | None, str]:
        process = await asyncio.create_subprocess_exec(
            *cmd, cwd=cwd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
        )
        try:
            stdout, _ = await asyncio.wait_for(process.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            return None, ""
        return process.returncode, stdout.decode(errors="replace")
