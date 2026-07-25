from abc import ABC, abstractmethod
from .models import GeneratedImage, ImageBrief


class ImageComposerPort(ABC):
    @abstractmethod
    def compose(self, image: GeneratedImage, brief: ImageBrief) -> bytes: ...


class ImageStoragePort(ABC):
    @abstractmethod
    async def upload(self, image_bytes: bytes, filename: str, project_id: str) -> str: ...
