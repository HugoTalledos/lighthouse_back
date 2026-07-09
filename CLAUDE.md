# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run all tests
python3 -m pytest -v

# Run a single test file
python3 -m pytest tests/unit/domain/test_models.py -v

# Run a single test by name
python3 -m pytest -v -k "test_tool_returns_dict_with_status"
```

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `OPENAI_API_KEY` | Yes (when `IMAGE_PROVIDER=dalle3`) | OpenAI API key with DALL-E 3 access |
| `FIREBASE_STORAGE_BUCKET` | Yes | Firebase Storage bucket name, e.g. `my-project.appspot.com` |
| `GOOGLE_APPLICATION_CREDENTIALS` | No | Path to Firebase service account JSON; omit to use Application Default Credentials |
| `IMAGE_PROVIDER` | No | `dalle3` (default) or `vertex` |

## Architecture

The only current feature is `image_builder_tool`, a LangGraph tool that generates Facebook/Instagram ad creatives from a business brief. The pipeline is: generate image → compose text overlay → upload to Firebase Storage.

The code follows **Domain-Driven Design** with a strict layering rule: inner layers have zero dependencies on outer layers.

```
src/agent/image_builder/
├── domain/          # Pure Python — no framework imports
│   ├── models.py          # Pydantic v2 value objects: ImageBrief, GeneratedImage, ComposedCreative, ImageBuildResult
│   ├── ports.py           # Abstract base classes: ImageGeneratorPort, ImageComposerPort, ImageStoragePort
│   └── prompt_builder.py  # Builds DALL-E prompts with per-variant mood variation
├── application/
│   └── image_builder_service.py  # Orchestrates generate → compose → upload; uses asyncio.gather for parallelism; isolates per-image failures
└── infrastructure/
    ├── dalle_generator.py   # DALL-E 3 via httpx (no openai SDK)
    ├── vertex_generator.py  # Vertex AI Imagen stub (raises NotImplementedError)
    ├── pillow_composer.py   # Pillow: 1200×628 crop + text bar + CTA pill
    └── firebase_storage.py  # Firebase Storage upload via asyncio.to_thread

image_builder_tool.py  # @tool entry point; _build_service() selects generator via IMAGE_PROVIDER env var
```

The `ImageBuilderService.build()` method uses `asyncio.gather(return_exceptions=True)` to run all image generation in parallel and isolate failures — a single variant failing does not abort the whole job. The `status` field in the result is `"success"` / `"partial"` / `"failed"` depending on how many variants succeeded.

### Adding a new image provider

1. Create `src/agent/image_builder/infrastructure/my_provider.py` implementing `ImageGeneratorPort`.
2. Register it in the `_GENERATORS` dict in `image_builder_tool.py`.
3. Set `IMAGE_PROVIDER=myprovider` at runtime.

## Testing

Tests are under `tests/` and mirror the `src/` structure:
- `tests/test_image_builder_tool.py` — integration-style tests for the `@tool` entry point (mocks `_build_service`)
- `tests/unit/domain/` — pure domain logic tests (no mocks needed)
- `tests/unit/application/` — service orchestration tests (mocks ports)
- `tests/unit/infrastructure/` — adapter tests (uses `pytest-httpx` for DALL-E HTTP mocking)

`pytest.ini` sets `asyncio_mode = auto`, so `async def test_*` functions work without decorators.
