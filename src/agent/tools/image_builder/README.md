# Lighthouse Back — image_builder Tool

LangGraph tool that generates Facebook/Instagram ad creatives from a business brief. Calls an image model through OpenRouter (or a local Ollama server), overlays headline + CTA text with Pillow, and uploads the result to Firebase Storage.

---

## Requirements

- Python 3.9+
- A Firebase project with a Storage bucket
- An OpenRouter API key (or a local Ollama server with an image model pulled)

---

## Installation

```bash
pip install -r requirements.txt
```

---

## Configuration

Set the following environment variables before running:

| Variable | Required | Description |
|---|---|---|
| `OPENROUTER_API_KEY` | Yes (when `IMAGE_PROVIDER=openrouter`) | OpenRouter API key |
| `FIREBASE_STORAGE_BUCKET` | Yes | Firebase Storage bucket name, e.g. `my-project.appspot.com` |
| `GOOGLE_APPLICATION_CREDENTIALS` | No | Path to Firebase service account JSON. If omitted, Application Default Credentials are used |
| `IMAGE_PROVIDER` | No | Image generation backend: `openrouter` (default) or `ollama` |
| `OPENROUTER_IMAGE_MODEL` | No | Image-capable model; defaults to `google/gemini-2.5-flash-image-preview` |
| `OLLAMA_BASE_URL` | No | Ollama server URL; defaults to `http://localhost:11434` |
| `OLLAMA_IMAGE_MODEL` | No | Ollama image model tag; defaults to `x/flux2-klein:4b` |

> **Note on resolution:** OpenRouter has no dedicated images endpoint — image models are called through `/chat/completions` and accept no width/height, so the target size is only a hint inside the prompt and the composer center-crops the result. Ollama does accept `width`/`height` directly.

### Firebase authentication

**Option A — Service account file (recommended for local dev):**
```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/serviceAccountKey.json"
```

**Option B — Application Default Credentials (Cloud Run, GKE, etc.):**
No extra config needed; the SDK picks up the environment's identity automatically.

---

## Usage

### As a LangGraph tool

```python
from src.agent.tools.image_builder.image_builder_tool import image_builder_tool

brief_dict = {
    "project_id": "my-campaign-001",
    "business_name": "Acme Co",
    "value_proposition": "Saves you 10 hours a week on invoicing",
    "target_customer": "Freelancers and small business owners",
    "headline": "Reclaim your week",          # max 40 chars
    "cta_text": "Start free trial",           # max 20 chars
    "style_hints": ["minimalist", "warm tones", "professional"],
    "n_images": 3,
}

# Inside an async context / LangGraph node:
result = await image_builder_tool.ainvoke({"brief_dict": brief_dict})

print(result["status"])          # "success" | "partial" | "failed"
print(result["errors"])          # list of per-image error messages (if any)

for creative in result["creatives"]:
    print(creative["storage_url"])   # public Firebase URL, ready for Meta Ads
    print(creative["headline"])
    print(creative["provider"])      # "openrouter"
```

### Wiring into a LangGraph agent

```python
from langgraph.prebuilt import create_react_agent
from src.agent.tools.image_builder.image_builder_tool import image_builder_tool

agent = create_react_agent(model, tools=[image_builder_tool])
```

---

## Output format

`image_builder_tool` returns a dict that serializes to:

```json
{
  "status": "success",
  "errors": [],
  "creatives": [
    {
      "variant_index": 0,
      "storage_url": "https://storage.googleapis.com/my-project.appspot.com/creatives/my-campaign-001/acme-co_0_20260708120000.png",
      "headline": "Reclaim your week",
      "cta_text": "Start free trial",
      "prompt_used": "A 1200x628 Facebook ad background image...",
      "provider": "openrouter",
      "image_bytes": "<base64-encoded PNG>"
    }
  ],
  "brief": { "...": "..." }
}
```

Generated images are uploaded to Firebase Storage at:
```
creatives/{project_id}/{business_name_slug}_{variant_index}_{timestamp}.png
```

---

## Architecture

```
src/agent/tools/image_builder/
├── domain/
│   ├── models.py            # Pydantic v2 value objects (ImageBrief, ImageBuildResult, …)
│   ├── ports.py             # Abstract ports (ImageComposerPort, ImageStoragePort)
│   └── prompt_builder.py    # Builds image prompts with per-variant mood variation
├── application/
│   └── image_builder_service.py  # Orchestrates: generate → compose → upload
├── infrastructure/
│   ├── composer/
│   │   └── pillow_composer.py       # Pillow: 1200×628 crop + text bar + CTA pill
│   └── storage/
│       └── firebase_storage.py      # Firebase Storage upload (non-blocking via asyncio.to_thread)
└── image_builder_tool.py    # @tool entry point + _build_service() factory
```

Image generation lives in `src/shared/image_gen/` (`ImageGeneratorPort`, the
OpenRouter and Ollama adapters, and `build_image_generator()`), shared with any
other tool that needs images — the same way `src/shared/llm/` serves text
generation.

The tool uses Domain-Driven Design: the domain layer has zero framework dependencies, infrastructure adapters are swapped via environment variables, and partial failures (one image fails) are isolated — the tool always returns whatever it managed to generate.

---

## Running tests

```bash
python3 -m pytest -v
```

Expected: the full suite green.

---

## Adding a new image provider

1. Create `src/shared/image_gen/infrastructure/my_provider.py` implementing `ImageGeneratorPort`:

```python
from ..domain.ports import ImageGeneratorPort
from ..domain.models import GeneratedImage

class MyProvider(ImageGeneratorPort):
    async def generate(self, prompt: str, width: int, height: int) -> GeneratedImage:
        # call your API here
        ...
```

2. Register it in `_GENERATORS` in `src/shared/image_gen/factory.py`:

```python
_GENERATORS = {
    "openrouter": OpenRouterImageGenerator,
    "ollama": OllamaImageGenerator,
    "myprovider": MyProvider,
}
```

3. Set `IMAGE_PROVIDER=myprovider` at runtime.
