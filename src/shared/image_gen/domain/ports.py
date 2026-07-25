from abc import ABC, abstractmethod
from .models import GeneratedImage


class ImageGeneratorPort(ABC):
    @abstractmethod
    async def generate(self, prompt: str, width: int, height: int) -> GeneratedImage: ...
