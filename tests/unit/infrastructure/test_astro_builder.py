from __future__ import annotations
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from src.agent.tools.landing_builder.infrastructure.astro_builder import AstroNodeBuilder


def _fake_process(returncode: int, output: bytes):
    process = MagicMock()
    process.communicate = AsyncMock(return_value=(output, None))
    process.returncode = returncode
    process.kill = MagicMock()
    process.wait = AsyncMock()
    return process


async def test_build_success_returns_dist_dir(monkeypatch):
    monkeypatch.setenv("LANDING_BUILD_TIMEOUT_SECONDS", "10")
    install_proc = _fake_process(0, b"installed\n")
    build_proc = _fake_process(0, b"built\n")

    with patch(
        "src.agent.tools.landing_builder.infrastructure.astro_builder.asyncio.create_subprocess_exec",
        AsyncMock(side_effect=[install_proc, build_proc]),
    ):
        builder = AstroNodeBuilder()
        result = await builder.build("/tmp/project")

    assert result.success is True
    assert result.dist_dir == "/tmp/project/dist"
    assert "installed" in result.logs
    assert "built" in result.logs


async def test_build_fails_when_npm_install_fails(monkeypatch):
    monkeypatch.setenv("LANDING_BUILD_TIMEOUT_SECONDS", "10")
    install_proc = _fake_process(1, b"npm error\n")

    with patch(
        "src.agent.tools.landing_builder.infrastructure.astro_builder.asyncio.create_subprocess_exec",
        AsyncMock(return_value=install_proc),
    ):
        builder = AstroNodeBuilder()
        result = await builder.build("/tmp/project")

    assert result.success is False
    assert result.dist_dir is None
    assert "npm error" in result.logs


async def test_build_fails_when_astro_build_fails(monkeypatch):
    monkeypatch.setenv("LANDING_BUILD_TIMEOUT_SECONDS", "10")
    install_proc = _fake_process(0, b"installed\n")
    build_proc = _fake_process(1, b"astro error\n")

    with patch(
        "src.agent.tools.landing_builder.infrastructure.astro_builder.asyncio.create_subprocess_exec",
        AsyncMock(side_effect=[install_proc, build_proc]),
    ):
        builder = AstroNodeBuilder()
        result = await builder.build("/tmp/project")

    assert result.success is False
    assert "astro error" in result.logs


async def test_build_treats_timeout_as_failure(monkeypatch):
    monkeypatch.setenv("LANDING_BUILD_TIMEOUT_SECONDS", "0.01")

    async def _hang():
        await asyncio.sleep(1)

    hanging_proc = MagicMock()
    hanging_proc.communicate = AsyncMock(side_effect=_hang)
    hanging_proc.kill = MagicMock()
    hanging_proc.wait = AsyncMock()

    with patch(
        "src.agent.tools.landing_builder.infrastructure.astro_builder.asyncio.create_subprocess_exec",
        AsyncMock(return_value=hanging_proc),
    ):
        builder = AstroNodeBuilder()
        result = await builder.build("/tmp/project")

    assert result.success is False
    assert "Timed out" in result.logs
