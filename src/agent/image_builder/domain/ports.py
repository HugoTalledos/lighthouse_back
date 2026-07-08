from abc import ABC, abstractmethod
from .models import GeneratedImage, ImageBrief


class ImageGeneratorPort(ABC):
    @abstractmethod
    async def generate(self, prompt: str, width: int, height: int) -> GeneratedImage: ...


class ImageComposerPort(ABC):
    @abstractmethod
    def compose(self, image: GeneratedImage, brief: ImageBrief) -> bytes: ...


class ImageStoragePort(ABC):
    @abstractmethod
    async def upload(self, image_bytes: bytes, filename: str, project_id: str) -> str: ...
