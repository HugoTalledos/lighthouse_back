from __future__ import annotations
from abc import ABC, abstractmethod


class TemplateSourcePort(ABC):
    @abstractmethod
    async def fetch(self, repo: str, ref: str) -> str:
        """Downloads and extracts the template into a fresh temp dir. Returns its path."""
        ...


class BuildResult:
    def __init__(self, success: bool, dist_dir: str | None, logs: str) -> None:
        self.success = success
        self.dist_dir = dist_dir
        self.logs = logs


class StaticBuilderPort(ABC):
    @abstractmethod
    async def build(self, project_dir: str) -> BuildResult:
        """Runs the static build (npm install && astro build) inside project_dir."""
        ...


class PreviewDeployment:
    def __init__(self, url: str, expire_time: str | None) -> None:
        self.url = url
        self.expire_time = expire_time


class HostingPort(ABC):
    @abstractmethod
    async def deploy_preview(self, dist_dir: str, channel_id: str) -> PreviewDeployment:
        """Deploys dist_dir to a Firebase Hosting preview channel, creating it if needed."""
        ...


class LandingStoragePort(ABC):
    @abstractmethod
    async def save_snapshot(self, project_id: str, version: str, project_dir: str) -> str:
        """Tars project_dir's source (excluding node_modules/.git/dist) and uploads it. Returns storage_path."""
        ...
