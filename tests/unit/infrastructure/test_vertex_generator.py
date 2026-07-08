import pytest
from src.agent.image_builder.infrastructure.vertex_generator import VertexImageGenerator


async def test_generate_raises_not_implemented():
    generator = VertexImageGenerator()
    with pytest.raises(NotImplementedError, match="TODO"):
        await generator.generate("A prompt", 1200, 628)
