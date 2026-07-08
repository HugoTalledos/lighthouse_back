# image_builder Tool — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `image_builder_tool` LangGraph tool that takes an `ImageBrief`, generates ad creative images via DALL-E 3, overlays headline + CTA with Pillow, uploads to Firebase Storage, and returns an `ImageBuildResult`.

**Architecture:** Domain-Driven Design with three layers — domain (pure Python value objects, ports, PromptBuilder), application (orchestrating service), infrastructure (DALL-E, Pillow, Firebase adapters) — wired together by a factory function in the tool layer. Partial failures are caught per-image so one failure never aborts the batch.

**Tech Stack:** Python 3.11+, Pydantic v2, httpx, Pillow, firebase-admin, langchain-core (`@tool`), pytest + pytest-asyncio + pytest-httpx.

## Global Constraints

- Pydantic v2 (`BaseModel`, `field_validator`, `model_validate`, `model_dump`)
- No `openai` SDK — use `httpx.AsyncClient` directly for DALL-E 3
- `headline` ≤ 40 chars, `cta_text` ≤ 20 chars — enforced by Pydantic validators
- DALL-E 3 model: `dall-e-3`, size: `1792x1024`, response_format: `url`
- Pillow target canvas: 1200×628 px, bottom bar height 140 px, alpha 160, CTA color `#1877F2`
- Firebase path pattern: `creatives/{project_id}/{filename}`, blobs are made public
- `IMAGE_PROVIDER` env var: `dalle3` (default) | `vertex`
- `@tool` decorator imported from `langchain_core.tools`
- All async tests use `pytest-asyncio` with `asyncio_mode = "auto"`

---

### Task 1: Project scaffold

**Files:**
- Create: `requirements.txt`
- Create: `pytest.ini`
- Create: `src/__init__.py`
- Create: `src/agent/__init__.py`
- Create: `src/agent/image_builder/__init__.py`
- Create: `src/agent/image_builder/domain/__init__.py`
- Create: `src/agent/image_builder/application/__init__.py`
- Create: `src/agent/image_builder/infrastructure/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/unit/__init__.py`
- Create: `tests/unit/domain/__init__.py`
- Create: `tests/unit/application/__init__.py`
- Create: `tests/unit/infrastructure/__init__.py`

**Interfaces:**
- Produces: importable `src.agent.image_builder` package; pytest configured for async tests

- [ ] **Step 1: Create `requirements.txt`**

```
pydantic>=2.0
httpx>=0.27
Pillow>=10.0
firebase-admin>=6.0
langchain-core>=0.2
langgraph>=0.1
pytest>=8.0
pytest-asyncio>=0.23
pytest-httpx>=0.30
```

- [ ] **Step 2: Create `pytest.ini`**

```ini
[pytest]
asyncio_mode = auto
```

- [ ] **Step 3: Create all `__init__.py` files**

Run:
```bash
touch src/__init__.py \
      src/agent/__init__.py \
      src/agent/image_builder/__init__.py \
      src/agent/image_builder/domain/__init__.py \
      src/agent/image_builder/application/__init__.py \
      src/agent/image_builder/infrastructure/__init__.py \
      tests/__init__.py \
      tests/unit/__init__.py \
      tests/unit/domain/__init__.py \
      tests/unit/application/__init__.py \
      tests/unit/infrastructure/__init__.py
```

- [ ] **Step 4: Install dependencies**

```bash
pip install -r requirements.txt
```

Expected: all packages install without error.

- [ ] **Step 5: Verify package is importable**

```bash
python -c "import src.agent.image_builder; print('OK')"
```

Expected output: `OK`

- [ ] **Step 6: Commit**

```bash
git add requirements.txt pytest.ini src/ tests/
git commit -m "chore: scaffold image_builder package and test structure"
```

---

### Task 2: Domain models

**Files:**
- Create: `src/agent/image_builder/domain/models.py`
- Create: `tests/unit/domain/test_models.py`

**Interfaces:**
- Produces:
  - `ImageBrief(project_id, business_name, value_proposition, target_customer, headline, cta_text, style_hints, n_images=3)`
  - `GeneratedImage(provider, image_bytes, prompt_used, width, height)`
  - `ComposedCreative(variant_index, image_bytes, storage_url, headline, cta_text, prompt_used, provider)`
  - `ImageBuildResult(brief, creatives, status, errors)` — status is `Literal["success", "partial", "failed"]`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/domain/test_models.py
import pytest
from pydantic import ValidationError
from src.agent.image_builder.domain.models import (
    ImageBrief, GeneratedImage, ComposedCreative, ImageBuildResult,
)


def _valid_brief(**overrides):
    data = dict(
        project_id="proj-1",
        business_name="Acme Co",
        value_proposition="Saves you 10 hours a week",
        target_customer="Busy professionals",
        headline="Save time every day",
        cta_text="Start free trial",
        style_hints=["minimalist", "warm tones"],
        n_images=3,
    )
    data.update(overrides)
    return data


def test_brief_roundtrip():
    brief = ImageBrief.model_validate(_valid_brief())
    assert brief.business_name == "Acme Co"
    assert brief.n_images == 3


def test_brief_default_n_images():
    data = _valid_brief()
    del data["n_images"]
    brief = ImageBrief.model_validate(data)
    assert brief.n_images == 3


def test_headline_too_long():
    with pytest.raises(ValidationError, match="headline"):
        ImageBrief.model_validate(_valid_brief(headline="x" * 41))


def test_cta_too_long():
    with pytest.raises(ValidationError, match="cta_text"):
        ImageBrief.model_validate(_valid_brief(cta_text="x" * 21))


def test_result_model_dump_is_serializable():
    brief = ImageBrief.model_validate(_valid_brief())
    creative = ComposedCreative(
        variant_index=0,
        image_bytes=b"fake",
        storage_url="https://example.com/img.png",
        headline="Save time every day",
        cta_text="Start free trial",
        prompt_used="A background...",
        provider="dalle3",
    )
    result = ImageBuildResult(
        brief=brief,
        creatives=[creative],
        status="success",
        errors=[],
    )
    dumped = result.model_dump()
    assert dumped["status"] == "success"
    assert dumped["creatives"][0]["provider"] == "dalle3"
    assert isinstance(dumped["brief"]["style_hints"], list)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/domain/test_models.py -v
```

Expected: `ModuleNotFoundError` or `ImportError` (models not yet created).

- [ ] **Step 3: Write `models.py`**

```python
# src/agent/image_builder/domain/models.py
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, field_validator


class ImageBrief(BaseModel):
    project_id: str
    business_name: str
    value_proposition: str
    target_customer: str
    headline: str
    cta_text: str
    style_hints: list[str]
    n_images: int = 3

    @field_validator("headline")
    @classmethod
    def headline_max_40(cls, v: str) -> str:
        if len(v) > 40:
            raise ValueError("headline must be ≤ 40 characters")
        return v

    @field_validator("cta_text")
    @classmethod
    def cta_max_20(cls, v: str) -> str:
        if len(v) > 20:
            raise ValueError("cta_text must be ≤ 20 characters")
        return v


class GeneratedImage(BaseModel):
    provider: str
    image_bytes: bytes
    prompt_used: str
    width: int
    height: int


class ComposedCreative(BaseModel):
    variant_index: int
    image_bytes: bytes
    storage_url: str | None
    headline: str
    cta_text: str
    prompt_used: str
    provider: str


class ImageBuildResult(BaseModel):
    brief: ImageBrief
    creatives: list[ComposedCreative]
    status: Literal["success", "partial", "failed"]
    errors: list[str]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/domain/test_models.py -v
```

Expected: 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/agent/image_builder/domain/models.py tests/unit/domain/test_models.py
git commit -m "feat: add domain models (ImageBrief, GeneratedImage, ComposedCreative, ImageBuildResult)"
```

---

### Task 3: Domain ports and PromptBuilder

**Files:**
- Create: `src/agent/image_builder/domain/ports.py`
- Create: `src/agent/image_builder/domain/prompt_builder.py`
- Create: `tests/unit/domain/test_prompt_builder.py`

**Interfaces:**
- Consumes: `ImageBrief`, `GeneratedImage` from Task 2
- Produces:
  - `ImageGeneratorPort.generate(prompt: str, width: int, height: int) -> GeneratedImage`
  - `ImageComposerPort.compose(image: GeneratedImage, brief: ImageBrief) -> bytes`
  - `ImageStoragePort.upload(image_bytes: bytes, filename: str, project_id: str) -> str`
  - `PromptBuilder.build_prompts(brief: ImageBrief) -> list[str]`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/domain/test_prompt_builder.py
from src.agent.image_builder.domain.models import ImageBrief
from src.agent.image_builder.domain.prompt_builder import PromptBuilder


def _brief(n_images=3):
    return ImageBrief(
        project_id="p1",
        business_name="Acme",
        value_proposition="Saves 10 hours a week",
        target_customer="Busy professionals",
        headline="Save time",
        cta_text="Try free",
        style_hints=["minimalist", "warm tones"],
        n_images=n_images,
    )


def test_returns_n_prompts():
    prompts = PromptBuilder().build_prompts(_brief(n_images=3))
    assert len(prompts) == 3


def test_each_prompt_contains_value_proposition():
    prompts = PromptBuilder().build_prompts(_brief())
    for p in prompts:
        assert "Saves 10 hours a week" in p


def test_each_prompt_contains_target_customer():
    prompts = PromptBuilder().build_prompts(_brief())
    for p in prompts:
        assert "Busy professionals" in p


def test_moods_cycle_for_more_than_3_variants():
    prompts = PromptBuilder().build_prompts(_brief(n_images=5))
    assert len(prompts) == 5
    assert "warm morning light" in prompts[0]
    assert "warm morning light" in prompts[3]


def test_negative_prompt_always_present():
    prompts = PromptBuilder().build_prompts(_brief())
    for p in prompts:
        assert "no text" in p.lower()
        assert "no watermarks" in p.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/domain/test_prompt_builder.py -v
```

Expected: `ImportError` (files not yet created).

- [ ] **Step 3: Write `ports.py`**

```python
# src/agent/image_builder/domain/ports.py
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
```

- [ ] **Step 4: Write `prompt_builder.py`**

```python
# src/agent/image_builder/domain/prompt_builder.py
from .models import ImageBrief

_MOODS = [
    "warm morning light",
    "cool evening tones",
    "neutral studio light",
]


class PromptBuilder:
    def build_prompts(self, brief: ImageBrief) -> list[str]:
        style = ", ".join(brief.style_hints) if brief.style_hints else "clean, professional"
        prompts = []
        for i in range(brief.n_images):
            mood = _MOODS[i % len(_MOODS)]
            prompt = (
                f"A 1200x628 Facebook ad background image. "
                f"Concept: {brief.value_proposition}. "
                f"Audience: {brief.target_customer}. "
                f"Style: {style}, {mood}. "
                f"No text, no watermarks, no logos, no UI elements."
            )
            prompts.append(prompt)
        return prompts
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/unit/domain/test_prompt_builder.py -v
```

Expected: 5 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add src/agent/image_builder/domain/ports.py \
        src/agent/image_builder/domain/prompt_builder.py \
        tests/unit/domain/test_prompt_builder.py
git commit -m "feat: add domain ports and PromptBuilder"
```

---

### Task 4: Application service

**Files:**
- Create: `src/agent/image_builder/application/image_builder_service.py`
- Create: `tests/unit/application/test_image_builder_service.py`

**Interfaces:**
- Consumes:
  - `ImageBrief`, `GeneratedImage`, `ComposedCreative`, `ImageBuildResult` from Task 2
  - `ImageGeneratorPort`, `ImageComposerPort`, `ImageStoragePort` from Task 3
  - `PromptBuilder.build_prompts(brief) -> list[str]` from Task 3
- Produces:
  - `ImageBuilderService(generator, composer, storage)`
  - `await ImageBuilderService.build(brief: ImageBrief) -> ImageBuildResult`
  - `_slugify(name: str) -> str` (module-private helper)

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/application/test_image_builder_service.py
import pytest
from src.agent.image_builder.domain.models import (
    ImageBrief, GeneratedImage, ComposedCreative, ImageBuildResult,
)
from src.agent.image_builder.domain.ports import (
    ImageGeneratorPort, ImageComposerPort, ImageStoragePort,
)
from src.agent.image_builder.application.image_builder_service import ImageBuilderService


def _brief(n_images=2):
    return ImageBrief(
        project_id="proj-abc",
        business_name="My Business",
        value_proposition="Saves time",
        target_customer="Professionals",
        headline="Save Time Now",
        cta_text="Get Started",
        style_hints=["clean"],
        n_images=n_images,
    )


def _fake_image(i=0):
    return GeneratedImage(
        provider="dalle3",
        image_bytes=b"fake-image-bytes",
        prompt_used=f"prompt {i}",
        width=1792,
        height=1024,
    )


class StubGenerator(ImageGeneratorPort):
    def __init__(self, side_effects):
        self._effects = iter(side_effects)

    async def generate(self, prompt, width, height):
        effect = next(self._effects)
        if isinstance(effect, Exception):
            raise effect
        return effect


class StubComposer(ImageComposerPort):
    def compose(self, image, brief):
        return b"composed-png-bytes"


class StubStorage(ImageStoragePort):
    async def upload(self, image_bytes, filename, project_id):
        return f"https://storage.example.com/{project_id}/{filename}"


async def test_all_succeed_returns_success():
    brief = _brief(n_images=2)
    service = ImageBuilderService(
        generator=StubGenerator([_fake_image(0), _fake_image(1)]),
        composer=StubComposer(),
        storage=StubStorage(),
    )
    result = await service.build(brief)
    assert result.status == "success"
    assert len(result.creatives) == 2
    assert result.errors == []


async def test_one_failure_returns_partial():
    brief = _brief(n_images=2)
    service = ImageBuilderService(
        generator=StubGenerator([RuntimeError("API down"), _fake_image(1)]),
        composer=StubComposer(),
        storage=StubStorage(),
    )
    result = await service.build(brief)
    assert result.status == "partial"
    assert len(result.creatives) == 1
    assert len(result.errors) == 1
    assert "Variant 0" in result.errors[0]


async def test_all_fail_returns_failed():
    brief = _brief(n_images=2)
    service = ImageBuilderService(
        generator=StubGenerator([RuntimeError("err"), RuntimeError("err")]),
        composer=StubComposer(),
        storage=StubStorage(),
    )
    result = await service.build(brief)
    assert result.status == "failed"
    assert len(result.creatives) == 0


async def test_creative_fields_populated():
    brief = _brief(n_images=1)
    service = ImageBuilderService(
        generator=StubGenerator([_fake_image(0)]),
        composer=StubComposer(),
        storage=StubStorage(),
    )
    result = await service.build(brief)
    creative = result.creatives[0]
    assert creative.variant_index == 0
    assert creative.headline == brief.headline
    assert creative.cta_text == brief.cta_text
    assert creative.provider == "dalle3"
    assert creative.storage_url.startswith("https://")


async def test_filename_contains_slugified_business_name():
    captured_filenames = []

    class CapturingStorage(ImageStoragePort):
        async def upload(self, image_bytes, filename, project_id):
            captured_filenames.append(filename)
            return f"https://example.com/{filename}"

    brief = _brief(n_images=1)
    service = ImageBuilderService(
        generator=StubGenerator([_fake_image(0)]),
        composer=StubComposer(),
        storage=CapturingStorage(),
    )
    await service.build(brief)
    assert captured_filenames[0].startswith("my-business_0_")
    assert captured_filenames[0].endswith(".png")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/application/test_image_builder_service.py -v
```

Expected: `ImportError` (service not yet created).

- [ ] **Step 3: Write `image_builder_service.py`**

```python
# src/agent/image_builder/application/image_builder_service.py
from __future__ import annotations
import asyncio
import re
from datetime import datetime

from ..domain.models import ImageBrief, ComposedCreative, ImageBuildResult
from ..domain.ports import ImageGeneratorPort, ImageComposerPort, ImageStoragePort
from ..domain.prompt_builder import PromptBuilder


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


class ImageBuilderService:
    def __init__(
        self,
        generator: ImageGeneratorPort,
        composer: ImageComposerPort,
        storage: ImageStoragePort,
    ) -> None:
        self._generator = generator
        self._composer = composer
        self._storage = storage

    async def build(self, brief: ImageBrief) -> ImageBuildResult:
        prompts = PromptBuilder().build_prompts(brief)
        results = await asyncio.gather(
            *[self._generator.generate(p, 1200, 628) for p in prompts],
            return_exceptions=True,
        )

        creatives: list[ComposedCreative] = []
        errors: list[str] = []
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                errors.append(f"Variant {i}: {result}")
                continue
            composed_bytes = self._composer.compose(result, brief)
            filename = f"{_slugify(brief.business_name)}_{i}_{timestamp}.png"
            url = await self._storage.upload(composed_bytes, filename, brief.project_id)
            creatives.append(
                ComposedCreative(
                    variant_index=i,
                    image_bytes=composed_bytes,
                    storage_url=url,
                    headline=brief.headline,
                    cta_text=brief.cta_text,
                    prompt_used=result.prompt_used,
                    provider=result.provider,
                )
            )

        if len(creatives) == brief.n_images:
            status = "success"
        elif len(creatives) > 0:
            status = "partial"
        else:
            status = "failed"

        return ImageBuildResult(
            brief=brief,
            creatives=creatives,
            status=status,
            errors=errors,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/application/test_image_builder_service.py -v
```

Expected: 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/agent/image_builder/application/image_builder_service.py \
        tests/unit/application/test_image_builder_service.py
git commit -m "feat: add ImageBuilderService with partial-failure handling"
```

---

### Task 5: DALL-E 3 adapter

**Files:**
- Create: `src/agent/image_builder/infrastructure/dalle_generator.py`
- Create: `tests/unit/infrastructure/test_dalle_generator.py`

**Interfaces:**
- Consumes: `GeneratedImage` from Task 2; `ImageGeneratorPort` from Task 3
- Produces: `DalleImageGenerator(ImageGeneratorPort)` — reads `OPENAI_API_KEY` from env

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/infrastructure/test_dalle_generator.py
import pytest
import httpx
from pytest_httpx import HTTPXMock
from src.agent.image_builder.infrastructure.dalle_generator import DalleImageGenerator


FAKE_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100  # minimal fake PNG bytes


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        DalleImageGenerator()


async def test_generate_returns_generated_image(monkeypatch, httpx_mock: HTTPXMock):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")

    image_url = "https://oaidalleapiprodscus.blob.core.windows.net/img.png"

    httpx_mock.add_response(
        method="POST",
        url="https://api.openai.com/v1/images/generations",
        json={"data": [{"url": image_url}]},
    )
    httpx_mock.add_response(
        method="GET",
        url=image_url,
        content=FAKE_PNG,
    )

    generator = DalleImageGenerator()
    result = await generator.generate("A background image", 1200, 628)

    assert result.provider == "dalle3"
    assert result.image_bytes == FAKE_PNG
    assert result.prompt_used == "A background image"
    assert result.width == 1792
    assert result.height == 1024


async def test_api_error_raises(monkeypatch, httpx_mock: HTTPXMock):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")

    httpx_mock.add_response(
        method="POST",
        url="https://api.openai.com/v1/images/generations",
        status_code=429,
        json={"error": {"message": "Rate limit exceeded"}},
    )

    generator = DalleImageGenerator()
    with pytest.raises(httpx.HTTPStatusError):
        await generator.generate("A prompt", 1200, 628)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/infrastructure/test_dalle_generator.py -v
```

Expected: `ImportError` (adapter not yet created).

- [ ] **Step 3: Write `dalle_generator.py`**

```python
# src/agent/image_builder/infrastructure/dalle_generator.py
from __future__ import annotations
import os
import httpx

from ..domain.models import GeneratedImage
from ..domain.ports import ImageGeneratorPort

_DALLE_URL = "https://api.openai.com/v1/images/generations"
_TIMEOUT = 60.0


class DalleImageGenerator(ImageGeneratorPort):
    def __init__(self) -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        self._api_key = api_key

    async def generate(self, prompt: str, width: int, height: int) -> GeneratedImage:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.post(
                _DALLE_URL,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "dall-e-3",
                    "prompt": prompt,
                    "n": 1,
                    "size": "1792x1024",
                    "response_format": "url",
                },
            )
            response.raise_for_status()
            image_url = response.json()["data"][0]["url"]

            image_response = await client.get(image_url)
            image_response.raise_for_status()

        return GeneratedImage(
            provider="dalle3",
            image_bytes=image_response.content,
            prompt_used=prompt,
            width=1792,
            height=1024,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/infrastructure/test_dalle_generator.py -v
```

Expected: 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/agent/image_builder/infrastructure/dalle_generator.py \
        tests/unit/infrastructure/test_dalle_generator.py
git commit -m "feat: add DalleImageGenerator adapter using httpx"
```

---

### Task 6: Vertex stub adapter

**Files:**
- Create: `src/agent/image_builder/infrastructure/vertex_generator.py`
- Create: `tests/unit/infrastructure/test_vertex_generator.py`

**Interfaces:**
- Consumes: `ImageGeneratorPort` from Task 3
- Produces: `VertexImageGenerator(ImageGeneratorPort)` — raises `NotImplementedError`

- [ ] **Step 1: Write failing test**

```python
# tests/unit/infrastructure/test_vertex_generator.py
import pytest
from src.agent.image_builder.infrastructure.vertex_generator import VertexImageGenerator


async def test_generate_raises_not_implemented():
    generator = VertexImageGenerator()
    with pytest.raises(NotImplementedError, match="TODO"):
        await generator.generate("A prompt", 1200, 628)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/unit/infrastructure/test_vertex_generator.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Write `vertex_generator.py`**

```python
# src/agent/image_builder/infrastructure/vertex_generator.py
from ..domain.models import GeneratedImage
from ..domain.ports import ImageGeneratorPort


class VertexImageGenerator(ImageGeneratorPort):
    async def generate(self, prompt: str, width: int, height: int) -> GeneratedImage:
        raise NotImplementedError("TODO: Vertex AI Imagen integration")
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/unit/infrastructure/test_vertex_generator.py -v
```

Expected: 1 test PASS.

- [ ] **Step 5: Commit**

```bash
git add src/agent/image_builder/infrastructure/vertex_generator.py \
        tests/unit/infrastructure/test_vertex_generator.py
git commit -m "feat: add VertexImageGenerator stub adapter"
```

---

### Task 7: Pillow image composer

**Files:**
- Create: `src/agent/image_builder/infrastructure/pillow_composer.py`
- Create: `tests/unit/infrastructure/test_pillow_composer.py`

**Interfaces:**
- Consumes: `GeneratedImage`, `ImageBrief` from Task 2; `ImageComposerPort` from Task 3
- Produces: `PillowImageComposer(ImageComposerPort)` — `compose(image, brief) -> bytes` (PNG)

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/infrastructure/test_pillow_composer.py
import io
import struct
import zlib
import pytest
from PIL import Image
from src.agent.image_builder.domain.models import ImageBrief, GeneratedImage
from src.agent.image_builder.infrastructure.pillow_composer import PillowImageComposer


def _make_png_bytes(width=1792, height=1024) -> bytes:
    img = Image.new("RGB", (width, height), color=(200, 100, 50))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _brief():
    return ImageBrief(
        project_id="p1",
        business_name="Acme",
        value_proposition="Saves time",
        target_customer="Professionals",
        headline="Save time every day",
        cta_text="Start free trial",
        style_hints=["clean"],
        n_images=1,
    )


def _fake_image(png_bytes: bytes) -> GeneratedImage:
    return GeneratedImage(
        provider="dalle3",
        image_bytes=png_bytes,
        prompt_used="prompt",
        width=1792,
        height=1024,
    )


def test_compose_returns_png_bytes():
    composer = PillowImageComposer()
    result = composer.compose(_fake_image(_make_png_bytes()), _brief())
    assert result[:8] == b"\x89PNG\r\n\x1a\n"


def test_compose_output_dimensions():
    composer = PillowImageComposer()
    result = composer.compose(_fake_image(_make_png_bytes()), _brief())
    img = Image.open(io.BytesIO(result))
    assert img.size == (1200, 628)


def test_compose_accepts_smaller_source_image():
    composer = PillowImageComposer()
    # 800x600 source — must be upscaled and cropped to 1200x628
    result = composer.compose(_fake_image(_make_png_bytes(800, 600)), _brief())
    img = Image.open(io.BytesIO(result))
    assert img.size == (1200, 628)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/infrastructure/test_pillow_composer.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Write `pillow_composer.py`**

```python
# src/agent/image_builder/infrastructure/pillow_composer.py
from __future__ import annotations
import io
from PIL import Image, ImageDraw, ImageFont

from ..domain.models import GeneratedImage, ImageBrief
from ..domain.ports import ImageComposerPort

_TARGET_W, _TARGET_H = 1200, 628
_BAR_H = 140
_BAR_ALPHA = 160
_CTA_COLOR = (24, 119, 242)  # #1877F2
_MARGIN = 24
_HEADLINE_SIZE = 48
_CTA_SIZE = 18
_FONT_PATHS = [
    "/System/Library/Fonts/Helvetica.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in _FONT_PATHS:
        try:
            return ImageFont.truetype(path, size)
        except (IOError, OSError):
            continue
    return ImageFont.load_default()


def _center_crop(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    src_w, src_h = img.size
    scale = max(target_w / src_w, target_h / src_h)
    new_w, new_h = int(src_w * scale), int(src_h * scale)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    return img.crop((left, top, left + target_w, top + target_h))


def _draw_wrapped_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    xy: tuple[int, int],
    max_width: int,
    fill: tuple[int, int, int, int],
) -> None:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), candidate, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)

    x, y = xy
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        bbox = draw.textbbox((0, 0), line, font=font)
        y += (bbox[3] - bbox[1]) + 4


def _draw_cta_pill(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    img_w: int,
    img_h: int,
    margin: int,
    color: tuple[int, int, int],
) -> None:
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    pad_x, pad_y = 16, 8
    pill_w = text_w + 2 * pad_x
    pill_h = text_h + 2 * pad_y
    x1 = img_w - margin - pill_w
    y1 = img_h - margin - pill_h
    x2 = img_w - margin
    y2 = img_h - margin
    r = pill_h // 2
    draw.rounded_rectangle([(x1, y1), (x2, y2)], radius=r, fill=(*color, 255))
    draw.text((x1 + pad_x, y1 + pad_y), text, font=font, fill=(255, 255, 255, 255))


class PillowImageComposer(ImageComposerPort):
    def compose(self, image: GeneratedImage, brief: ImageBrief) -> bytes:
        img = Image.open(io.BytesIO(image.image_bytes)).convert("RGBA")
        img = _center_crop(img, _TARGET_W, _TARGET_H)

        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        bar_y = _TARGET_H - _BAR_H
        draw.rectangle([(0, bar_y), (_TARGET_W, _TARGET_H)], fill=(0, 0, 0, _BAR_ALPHA))

        headline_font = _load_font(_HEADLINE_SIZE)
        _draw_wrapped_text(
            draw,
            brief.headline,
            headline_font,
            (_MARGIN, bar_y + 16),
            _TARGET_W - 2 * _MARGIN,
            (255, 255, 255, 255),
        )

        cta_font = _load_font(_CTA_SIZE)
        _draw_cta_pill(draw, brief.cta_text, cta_font, _TARGET_W, _TARGET_H, _MARGIN, _CTA_COLOR)

        result = Image.alpha_composite(img, overlay).convert("RGB")
        buf = io.BytesIO()
        result.save(buf, format="PNG")
        return buf.getvalue()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/infrastructure/test_pillow_composer.py -v
```

Expected: 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/agent/image_builder/infrastructure/pillow_composer.py \
        tests/unit/infrastructure/test_pillow_composer.py
git commit -m "feat: add PillowImageComposer with center-crop, text bar, and CTA pill"
```

---

### Task 8: Firebase Storage adapter

**Files:**
- Create: `src/agent/image_builder/infrastructure/firebase_storage.py`
- Create: `tests/unit/infrastructure/test_firebase_storage.py`

**Interfaces:**
- Consumes: `ImageStoragePort` from Task 3
- Produces: `FirebaseStorageAdapter(ImageStoragePort)` — reads `FIREBASE_STORAGE_BUCKET` from env

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/infrastructure/test_firebase_storage.py
import pytest
from unittest.mock import MagicMock, patch
from src.agent.image_builder.infrastructure.firebase_storage import FirebaseStorageAdapter


def test_missing_bucket_raises(monkeypatch):
    monkeypatch.delenv("FIREBASE_STORAGE_BUCKET", raising=False)
    with pytest.raises(ValueError, match="FIREBASE_STORAGE_BUCKET"):
        FirebaseStorageAdapter()


async def test_upload_calls_make_public_and_returns_url(monkeypatch):
    monkeypatch.setenv("FIREBASE_STORAGE_BUCKET", "my-project.appspot.com")

    fake_blob = MagicMock()
    fake_blob.public_url = "https://storage.googleapis.com/my-project.appspot.com/creatives/proj-1/img.png"

    fake_bucket = MagicMock()
    fake_bucket.blob.return_value = fake_blob

    with patch("src.agent.image_builder.infrastructure.firebase_storage.firebase_admin") as mock_admin, \
         patch("src.agent.image_builder.infrastructure.firebase_storage.fb_storage") as mock_storage:
        mock_admin._apps = {"[DEFAULT]": True}
        mock_storage.bucket.return_value = fake_bucket

        adapter = FirebaseStorageAdapter()
        url = await adapter.upload(b"png-bytes", "img.png", "proj-1")

    fake_bucket.blob.assert_called_once_with("creatives/proj-1/img.png")
    fake_blob.upload_from_string.assert_called_once_with(b"png-bytes", content_type="image/png")
    fake_blob.make_public.assert_called_once()
    assert url == "https://storage.googleapis.com/my-project.appspot.com/creatives/proj-1/img.png"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/infrastructure/test_firebase_storage.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Write `firebase_storage.py`**

```python
# src/agent/image_builder/infrastructure/firebase_storage.py
from __future__ import annotations
import os
import firebase_admin
from firebase_admin import storage as fb_storage

from ..domain.ports import ImageStoragePort


class FirebaseStorageAdapter(ImageStoragePort):
    def __init__(self) -> None:
        bucket_name = os.getenv("FIREBASE_STORAGE_BUCKET")
        if not bucket_name:
            raise ValueError("FIREBASE_STORAGE_BUCKET environment variable is not set")
        self._bucket_name = bucket_name
        if not firebase_admin._apps:
            firebase_admin.initialize_app(options={"storageBucket": bucket_name})

    async def upload(self, image_bytes: bytes, filename: str, project_id: str) -> str:
        bucket = fb_storage.bucket(self._bucket_name)
        blob = bucket.blob(f"creatives/{project_id}/{filename}")
        blob.upload_from_string(image_bytes, content_type="image/png")
        blob.make_public()
        return blob.public_url
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/infrastructure/test_firebase_storage.py -v
```

Expected: 2 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/agent/image_builder/infrastructure/firebase_storage.py \
        tests/unit/infrastructure/test_firebase_storage.py
git commit -m "feat: add FirebaseStorageAdapter"
```

---

### Task 9: Tool layer

**Files:**
- Create: `src/agent/image_builder/image_builder_tool.py`
- Create: `tests/test_image_builder_tool.py`

**Interfaces:**
- Consumes: all adapters from Tasks 5–8; `ImageBuilderService` from Task 4; `ImageBrief` from Task 2
- Produces:
  - `_build_service() -> ImageBuilderService` (reads `IMAGE_PROVIDER` env var)
  - `image_builder_tool(brief_dict: dict) -> dict` (LangGraph `@tool`)

- [ ] **Step 1: Write failing tests**

```python
# tests/test_image_builder_tool.py
import io
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from pydantic import ValidationError
from PIL import Image

from src.agent.image_builder.domain.models import (
    ImageBrief, GeneratedImage, ComposedCreative, ImageBuildResult,
)


def _valid_brief_dict():
    return dict(
        project_id="proj-1",
        business_name="Acme",
        value_proposition="Saves time",
        target_customer="Professionals",
        headline="Save time",
        cta_text="Try free",
        style_hints=["clean"],
        n_images=1,
    )


def _stub_result(brief):
    creative = ComposedCreative(
        variant_index=0,
        image_bytes=b"png",
        storage_url="https://example.com/img.png",
        headline=brief.headline,
        cta_text=brief.cta_text,
        prompt_used="prompt",
        provider="dalle3",
    )
    return ImageBuildResult(brief=brief, creatives=[creative], status="success", errors=[])


async def test_tool_returns_dict_with_status(monkeypatch):
    monkeypatch.setenv("IMAGE_PROVIDER", "dalle3")

    brief = ImageBrief.model_validate(_valid_brief_dict())
    stub_result = _stub_result(brief)

    with patch(
        "src.agent.image_builder.image_builder_tool._build_service"
    ) as mock_factory:
        mock_service = MagicMock()
        mock_service.build = AsyncMock(return_value=stub_result)
        mock_factory.return_value = mock_service

        from src.agent.image_builder.image_builder_tool import image_builder_tool
        result = await image_builder_tool.ainvoke({"brief_dict": _valid_brief_dict()})

    assert result["status"] == "success"
    assert len(result["creatives"]) == 1


async def test_tool_raises_on_invalid_brief():
    from src.agent.image_builder.image_builder_tool import image_builder_tool
    with pytest.raises(Exception):
        await image_builder_tool.ainvoke({"brief_dict": {"business_name": "Only this"}})


def test_build_service_selects_dalle_by_default(monkeypatch):
    monkeypatch.setenv("IMAGE_PROVIDER", "dalle3")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("FIREBASE_STORAGE_BUCKET", "test.appspot.com")

    with patch("src.agent.image_builder.infrastructure.firebase_storage.firebase_admin") as m:
        m._apps = {"[DEFAULT]": True}
        from src.agent.image_builder.image_builder_tool import _build_service
        from src.agent.image_builder.infrastructure.dalle_generator import DalleImageGenerator
        service = _build_service()
        assert isinstance(service._generator, DalleImageGenerator)


def test_build_service_selects_vertex(monkeypatch):
    monkeypatch.setenv("IMAGE_PROVIDER", "vertex")
    monkeypatch.setenv("FIREBASE_STORAGE_BUCKET", "test.appspot.com")

    with patch("src.agent.image_builder.infrastructure.firebase_storage.firebase_admin") as m:
        m._apps = {"[DEFAULT]": True}
        from src.agent.image_builder.image_builder_tool import _build_service
        from src.agent.image_builder.infrastructure.vertex_generator import VertexImageGenerator
        service = _build_service()
        assert isinstance(service._generator, VertexImageGenerator)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_image_builder_tool.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Write `image_builder_tool.py`**

```python
# src/agent/image_builder/image_builder_tool.py
from __future__ import annotations
import os
from langchain_core.tools import tool

from .domain.models import ImageBrief
from .application.image_builder_service import ImageBuilderService
from .infrastructure.dalle_generator import DalleImageGenerator
from .infrastructure.vertex_generator import VertexImageGenerator
from .infrastructure.pillow_composer import PillowImageComposer
from .infrastructure.firebase_storage import FirebaseStorageAdapter


def _build_service() -> ImageBuilderService:
    provider = os.getenv("IMAGE_PROVIDER", "dalle3")
    generator = DalleImageGenerator() if provider == "dalle3" else VertexImageGenerator()
    composer = PillowImageComposer()
    storage = FirebaseStorageAdapter()
    return ImageBuilderService(generator, composer, storage)


@tool
async def image_builder_tool(brief_dict: dict) -> dict:
    """
    Generates ad creative images for a business validation campaign.
    Input: serialized ImageBrief dict.
    Output: serialized ImageBuildResult dict.
    """
    brief = ImageBrief.model_validate(brief_dict)
    service = _build_service()
    result = await service.build(brief)
    return result.model_dump()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_image_builder_tool.py -v
```

Expected: 4 tests PASS.

- [ ] **Step 5: Run full test suite**

```bash
pytest -v
```

Expected: all tests PASS (no failures, no errors).

- [ ] **Step 6: Commit**

```bash
git add src/agent/image_builder/image_builder_tool.py \
        tests/test_image_builder_tool.py
git commit -m "feat: add image_builder_tool LangGraph tool with factory wiring"
```

---

## Self-Review Checklist

- [x] **Spec coverage:** All 4 domain models ✓, 3 ports ✓, PromptBuilder ✓, ImageBuilderService ✓, DalleImageGenerator ✓, VertexImageGenerator stub ✓, PillowImageComposer (all 6 steps) ✓, FirebaseStorageAdapter ✓, `@tool` entry point ✓, `_build_service()` factory ✓, `IMAGE_PROVIDER` env var ✓
- [x] **Placeholder scan:** No TBDs or TODOs in plan steps (VertexImageGenerator stub intentionally raises `NotImplementedError` — this is the spec requirement, not a placeholder)
- [x] **Type consistency:** `ImageStoragePort.upload(image_bytes, filename, project_id)` signature is consistent across ports.py, service, adapter, and tests; `GeneratedImage` and `ImageBrief` used correctly in composer throughout
- [x] **`_slugify` defined:** implemented in `image_builder_service.py`, tested via `test_filename_contains_slugified_business_name`
