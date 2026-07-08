# image_builder Tool — Design Spec
**Date:** 2026-07-08  
**Status:** Approved  
**Project:** Lighthouse — Phase 2 (Generation)

---

## 1. Purpose

`image_builder_tool` is a LangGraph `@tool` that generates Facebook/Instagram ad creatives for a business validation campaign. Given a structured brief, it produces `n` composed PNG images (raw AI image + text overlay) uploaded to Firebase Storage, ready for Meta Ads.

---

## 2. File Structure

```
src/agent/image_builder/
├── domain/
│   ├── __init__.py
│   ├── models.py              # Value objects and aggregate root (Pydantic v2)
│   ├── ports.py               # Abstract ports (ABC)
│   └── prompt_builder.py      # PromptBuilder domain service
├── application/
│   ├── __init__.py
│   └── image_builder_service.py
├── infrastructure/
│   ├── __init__.py
│   ├── dalle_generator.py     # DalleImageGenerator
│   ├── vertex_generator.py    # VertexImageGenerator (stub)
│   ├── pillow_composer.py     # PillowImageComposer
│   └── firebase_storage.py    # FirebaseStorageAdapter
└── image_builder_tool.py      # @tool entry point + _build_service() factory
```

---

## 3. Domain Layer (`domain/`)

### 3.1 Models (`models.py`)

All models are Pydantic v2 `BaseModel` (immutable value objects / aggregate root).

**`ImageBrief`** — input to the tool:
| Field | Type | Constraint |
|---|---|---|
| `project_id` | `str` | Firebase storage path key |
| `business_name` | `str` | — |
| `value_proposition` | `str` | From clarification brief |
| `target_customer` | `str` | — |
| `headline` | `str` | ≤ 40 chars |
| `cta_text` | `str` | ≤ 20 chars |
| `style_hints` | `list[str]` | e.g. `["minimalist", "warm tones"]` |
| `n_images` | `int` | Default `3` |

**`GeneratedImage`** — raw output from the image provider:
| Field | Type |
|---|---|
| `provider` | `str` — `"dalle3"` \| `"vertex_imagen"` \| `"stability"` |
| `image_bytes` | `bytes` |
| `prompt_used` | `str` |
| `width` | `int` |
| `height` | `int` |

**`ComposedCreative`** — final artifact after Pillow composition + storage upload:
| Field | Type |
|---|---|
| `variant_index` | `int` |
| `image_bytes` | `bytes` |
| `storage_url` | `str \| None` |
| `headline` | `str` |
| `cta_text` | `str` |
| `prompt_used` | `str` |
| `provider` | `str` |

**`ImageBuildResult`** — aggregate root returned by the service:
| Field | Type |
|---|---|
| `brief` | `ImageBrief` |
| `creatives` | `list[ComposedCreative]` |
| `status` | `Literal["success", "partial", "failed"]` |
| `errors` | `list[str]` |

Status rules:
- `"success"` — all `n_images` generated successfully
- `"partial"` — at least 1 creative succeeded, some failed
- `"failed"` — 0 creatives generated

### 3.2 Ports (`ports.py`)

```python
class ImageGeneratorPort(ABC):
    async def generate(self, prompt: str, width: int, height: int) -> GeneratedImage: ...

class ImageComposerPort(ABC):
    def compose(self, image: GeneratedImage, brief: ImageBrief) -> bytes: ...

class ImageStoragePort(ABC):
    async def upload(self, image_bytes: bytes, filename: str, project_id: str) -> str: ...
```

### 3.3 PromptBuilder (`prompt_builder.py`)

Domain service. Stateless. `build_prompts(brief: ImageBrief) -> list[str]`.

Produces exactly `brief.n_images` prompts. Each prompt:
- Requests a 1200×628px Facebook ad background (no text in image)
- Encodes `value_proposition`, `target_customer`, and `style_hints`
- Applies a per-variant mood modifier from a fixed set:
  - variant 0: `"warm morning light"`
  - variant 1: `"cool evening tones"`
  - variant 2: `"neutral studio light"`
  - variant n≥3: cycles through the set
- Appends fixed negative prompt: `"no text, no watermarks, no logos, no UI elements"`

---

## 4. Application Layer (`application/`)

### `ImageBuilderService`

```python
class ImageBuilderService:
    def __init__(
        self,
        generator: ImageGeneratorPort,
        composer: ImageComposerPort,
        storage: ImageStoragePort,
    ): ...

    async def build(self, brief: ImageBrief) -> ImageBuildResult: ...
```

**Orchestration flow:**

1. `prompts = PromptBuilder().build_prompts(brief)`
2. `results = await asyncio.gather(*[generator.generate(p, 1200, 628) for p in prompts], return_exceptions=True)`
3. For each result:
   - If `Exception` → append error message to `errors`, skip
   - If `GeneratedImage` → `composer.compose(image, brief)` → PNG bytes
   - `filename = f"{slugify(brief.business_name)}_{i}_{timestamp}.png"` where `slugify` is a local helper: `re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')`
   - `url = await storage.upload(bytes, filename, brief.project_id)`
   - Append `ComposedCreative(...)`
4. Compute `status` from `len(creatives)` vs `len(errors)`
5. Return `ImageBuildResult`

Generation runs concurrently (`asyncio.gather`). Pillow composition is called synchronously (3 images × ~100ms is acceptable without a thread pool). Storage uploads run sequentially after each composition.

---

## 5. Infrastructure Layer (`infrastructure/`)

### 5.1 `DalleImageGenerator`

- Uses `httpx.AsyncClient` (no openai SDK).
- Endpoint: `POST https://api.openai.com/v1/images/generations`
- Model: `dall-e-3`, size `1792x1024` (closest to 16:9; Pillow crops to 1200×628).
- Response: URL to temporary image → downloads bytes via `httpx`.
- Config: `OPENAI_API_KEY` env var (raises `ValueError` in `__init__` if missing).
- Timeout: 60s.

### 5.2 `VertexImageGenerator` (stub)

Raises `NotImplementedError("TODO: Vertex AI Imagen integration")`.  
Exists to prove the port abstraction is provider-agnostic.

### 5.3 `PillowImageComposer`

Steps applied to each image:
1. Decode bytes → PIL Image, convert to RGBA.
2. Resize/center-crop to 1200×628.
3. Draw semi-transparent bottom bar: black, alpha=160, height=140px.
4. Render `headline` in bold white, ~48px. Font: system TrueType if available, else `ImageFont.load_default()`. Text wraps within bar width.
5. Render `cta_text` in a pill shape (fill `#1877F2`, white text, ~18px) anchored to bottom-right corner with 24px margin.
6. Encode to PNG via `BytesIO`, return bytes.

### 5.4 `FirebaseStorageAdapter`

- Initializes `firebase_admin` app (if not already initialized) using ADC or `GOOGLE_APPLICATION_CREDENTIALS`.
- Bucket: `FIREBASE_STORAGE_BUCKET` env var (raises `ValueError` if missing).
- Upload path: `creatives/{project_id}/{filename}`.
- Calls `blob.make_public()` and returns `blob.public_url`. Ad images are public assets by design.

---

## 6. Tool Layer (`image_builder_tool.py`)

### Environment variables

| Var | Values | Default | Effect |
|---|---|---|---|
| `IMAGE_PROVIDER` | `dalle3` \| `vertex` | `dalle3` | Selects image generator adapter |
| `OPENAI_API_KEY` | string | — | Required when `IMAGE_PROVIDER=dalle3` |
| `FIREBASE_STORAGE_BUCKET` | string | — | Always required (no local fallback) |
| `GOOGLE_APPLICATION_CREDENTIALS` | path | — | Firebase auth (ADC if omitted) |

### Factory

```python
def _build_service() -> ImageBuilderService:
    provider = os.getenv("IMAGE_PROVIDER", "dalle3")
    generator = DalleImageGenerator() if provider == "dalle3" else VertexImageGenerator()
    composer = PillowImageComposer()
    storage = FirebaseStorageAdapter()
    return ImageBuilderService(generator, composer, storage)
```

### Tool

```python
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

---

## 7. Error Handling

- Per-image failures are caught by `asyncio.gather(return_exceptions=True)` and recorded in `ImageBuildResult.errors`. The tool never raises unless `ImageBrief` validation fails (malformed input from the agent).
- Adapter `__init__` methods validate env vars eagerly and raise `ValueError` with clear messages, so misconfiguration surfaces at startup rather than mid-run.

---

## 8. Key Dependencies

| Package | Purpose |
|---|---|
| `pydantic>=2` | Models / validation |
| `httpx` | DALL-E 3 API calls (async) |
| `Pillow` | Image composition |
| `firebase-admin` | Firebase Storage upload |
| `langgraph` | `@tool` decorator |
