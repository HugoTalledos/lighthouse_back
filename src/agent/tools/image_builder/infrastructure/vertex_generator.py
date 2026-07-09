from ..domain.models import GeneratedImage
from ..domain.ports import ImageGeneratorPort


class VertexImageGenerator(ImageGeneratorPort):
    async def generate(self, prompt: str, width: int, height: int) -> GeneratedImage:
        raise NotImplementedError("TODO: Vertex AI Imagen integration")
