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
There are two independent provider axes: `LLM_PROVIDER` (text/JSON generation) and `IMAGE_PROVIDER` (image generation). Both accept only `openrouter` (default) or `ollama`.

| Variable | Required | Description |
|---|---|---|
| `OPENROUTER_API_KEY` | Yes (when either provider is `openrouter`) | OpenRouter API key; shared by the LLM client and the image generator |
| `LLM_PROVIDER` | No | `openrouter` (default) or `ollama` |
| `OPENROUTER_MODEL` | No | Chat model in `vendor/model` form; defaults to `openai/gpt-4o` |
| `OLLAMA_MODEL` | No (when `LLM_PROVIDER=ollama`) | Ollama chat model tag; defaults to `llama3.1` |
| `IMAGE_PROVIDER` | No | `openrouter` (default) or `ollama` |
| `OPENROUTER_IMAGE_MODEL` | No | Image-capable model; defaults to `google/gemini-2.5-flash-image-preview` |
| `OLLAMA_BASE_URL` | No (when either provider is `ollama`) | Ollama server URL; defaults to `http://localhost:11434` |
| `OLLAMA_IMAGE_MODEL` | No (when `IMAGE_PROVIDER=ollama`) | Ollama image model tag; defaults to `x/flux2-klein:4b` |
| `FIREBASE_STORAGE_BUCKET` | Yes | Firebase Storage bucket name, e.g. `my-project.appspot.com` |
| `GOOGLE_APPLICATION_CREDENTIALS` | No | Path to Firebase service account JSON; omit to use Application Default Credentials |

## Architecture

The only current feature is `image_builder_tool`, a LangGraph tool that generates Facebook/Instagram ad creatives from a business brief. The pipeline is: generate image → compose text overlay → upload to Firebase Storage.

The code follows **Domain-Driven Design** with a strict layering rule: inner layers have zero dependencies on outer layers.

```
src/agent/tools/image_builder/
├── domain/          # Pure Python — no framework imports
│   ├── models.py          # Pydantic v2 value objects: ImageBrief, ComposedCreative, ImageBuildResult (re-exports GeneratedImage from shared)
│   ├── ports.py           # Abstract base classes: ImageComposerPort, ImageStoragePort
│   └── prompt_builder.py  # Builds image prompts with per-variant mood variation
├── application/
│   └── image_builder_service.py  # Orchestrates generate → compose → upload; uses asyncio.gather for parallelism; isolates per-image failures
└── infrastructure/
    ├── composer/pillow_composer.py   # Pillow: 1200×628 crop + text bar + CTA pill
    └── storage/firebase_storage.py   # Firebase Storage upload via asyncio.to_thread

image_builder_tool.py  # @tool entry point; builds the generator via src/shared/image_gen

src/shared/
├── openrouter/credentials.py   # OpenRouterCredentials: env read once, shared by the LLM and image clients
├── llm/                        # LLMClientPort + OpenRouter/Ollama clients; build_llm_client() ← LLM_PROVIDER
└── image_gen/                  # ImageGeneratorPort + OpenRouter/Ollama generators; build_image_generator() ← IMAGE_PROVIDER
```

The `ImageBuilderService.build()` method uses `asyncio.gather(return_exceptions=True)` to run all image generation in parallel and isolate failures — a single variant failing does not abort the whole job. The `status` field in the result is `"success"` / `"partial"` / `"failed"` depending on how many variants succeeded.

### Adding a new image provider

1. Create `src/shared/image_gen/infrastructure/my_provider.py` implementing `ImageGeneratorPort`.
2. Register it in the `_GENERATORS` dict in `src/shared/image_gen/factory.py`.
3. Set `IMAGE_PROVIDER=myprovider` at runtime.

## Testing

Tests are under `tests/` and mirror the `src/` structure:
- `tests/test_image_builder_tool.py` — integration-style tests for the `@tool` entry point (mocks `_build_service`)
- `tests/unit/domain/` — pure domain logic tests (no mocks needed)
- `tests/unit/application/` — service orchestration tests (mocks ports)
- `tests/unit/infrastructure/` — adapter tests (uses `pytest-httpx` to mock provider HTTP calls)

`pytest.ini` sets `asyncio_mode = auto`, so `async def test_*` functions work without decorators.
