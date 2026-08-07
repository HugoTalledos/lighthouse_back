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
| `API_KEY` | No | Si está seteada, `/chat` y `/projects` exigen el header `x-api-key`. Sin ella el API queda abierto |
| `ALLOWED_ORIGINS` | No | Orígenes CORS separados por comas; default `*` |

## Architecture

`src/agent/tools/` currently holds four LangGraph tools: `campaign_builder_tool` (generates a Facebook Marketing API campaign config from a business brief), `landing_builder_tool` (generates and previews a landing page), `promote_landing_tool` (persists an approved landing to permanent storage), and `image_builder_tool`, which generates Facebook/Instagram ad creatives from a business brief. The rest of this section documents `image_builder_tool`'s pipeline: generate image → compose text overlay → upload to Firebase Storage.

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

## HTTP API

`src/main.py` es el composition root: monta `POST /chat` (SSE) y las rutas de
`/projects`, con CORS y auth por API key.

```bash
uvicorn src.main:app --reload --workers 1
```

`POST /chat` recibe `{"message": str, "thread_id": str | null}` y responde
`text/event-stream` con eventos `start`, `message`, `tool_call`, `tool_result`,
`done` y `error`. Si `thread_id` viene vacío el API genera uno y lo devuelve en
el evento `start`; el cliente debe reenviarlo en los siguientes turnos.

El evento `tool_result` lleva un campo `status`. Las tools de construcción
(`campaign_builder_tool`, `image_builder_tool`, `landing_builder_tool`,
`promote_landing_tool`) devuelven `"success"` / `"partial"` / `"failed"`
(`"partial"` solo aplica a `image_builder_tool`, cuando algunas variantes
fallan y otras no); las tools de aprobación (`approve_images_tool`,
`approve_campaign_tool`) devuelven `"approved"` / `"failed"`.

**El checkpointer es `MemorySaver` (en memoria), así que el API debe correr con
un solo worker.** Con varios workers, dos turnos de la misma conversación pueden
aterrizar en procesos distintos y perder el contexto. El historial también se
pierde al reiniciar. Además, `MemorySaver` nunca desaloja: la memoria crece
monótonamente con cada `thread_id` visto (cada `POST /chat` sin `thread_id`
crea uno nuevo), y hoy la única forma de liberarla es reiniciar el proceso.

## Testing

Tests are under `tests/` and mirror the `src/` structure:
- `tests/test_image_builder_tool.py` — integration-style tests for the `@tool` entry point (mocks `_build_service`)
- `tests/unit/domain/` — pure domain logic tests (no mocks needed)
- `tests/unit/application/` — service orchestration tests (mocks ports)
- `tests/unit/infrastructure/` — adapter tests for image_builder's composer and storage, plus other tools' infrastructure adapters
- `tests/unit/shared/` — shared LLM and image-generation modules: factory dispatch tests plus provider adapter tests (uses `pytest-httpx` to mock HTTP calls)

`pytest.ini` sets `asyncio_mode = auto`, so `async def test_*` functions work without decorators.
