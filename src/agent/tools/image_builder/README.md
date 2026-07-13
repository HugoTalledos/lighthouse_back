# Lighthouse Back — image_builder Tool

LangGraph tool that generates Facebook/Instagram ad creatives from a business brief. Calls DALL-E 3, overlays headline + CTA text with Pillow, and uploads the result to Firebase Storage.

---

## Requirements

- Python 3.9+
- A Firebase project with a Storage bucket
- An OpenAI API key with DALL-E 3 access

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
| `OPENAI_API_KEY` | Yes (when `IMAGE_PROVIDER=dalle3`) | OpenAI API key with DALL-E 3 access |
| `FIREBASE_STORAGE_BUCKET` | Yes | Firebase Storage bucket name, e.g. `my-project.appspot.com` |
| `GOOGLE_APPLICATION_CREDENTIALS` | No | Path to Firebase service account JSON. If omitted, Application Default Credentials are used |
| `IMAGE_PROVIDER` | No | Image generation backend: `dalle3` (default) or `vertex` |

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
    print(creative["provider"])      # "dalle3"
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
      "provider": "dalle3",
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
src/agent/image_builder/
├── domain/
│   ├── models.py            # Pydantic v2 value objects (ImageBrief, ImageBuildResult, …)
│   ├── ports.py             # Abstract ports (ImageGeneratorPort, ImageComposerPort, ImageStoragePort)
│   └── prompt_builder.py   # Builds DALL-E prompts with per-variant mood variation
├── application/
│   └── image_builder_service.py  # Orchestrates: generate → compose → upload
├── infrastructure/
│   ├── dalle_generator.py   # DALL-E 3 via httpx (no openai SDK)
│   ├── vertex_generator.py  # Vertex AI Imagen stub (NotImplementedError)
│   ├── pillow_composer.py   # Pillow: 1200×628 crop + text bar + CTA pill
│   └── firebase_storage.py  # Firebase Storage upload (non-blocking via asyncio.to_thread)
└── image_builder_tool.py    # @tool entry point + _build_service() factory
```

The tool uses Domain-Driven Design: the domain layer has zero framework dependencies, infrastructure adapters are swapped via environment variables, and partial failures (one image fails) are isolated — the tool always returns whatever it managed to generate.

---

## Running tests

```bash
python3 -m pytest -v
```

Expected: 28 tests, all passing.

---

## Adding a new image provider

1. Create `src/agent/image_builder/infrastructure/my_provider.py` implementing `ImageGeneratorPort`:

```python
from ..domain.ports import ImageGeneratorPort
from ..domain.models import GeneratedImage

class MyProvider(ImageGeneratorPort):
    async def generate(self, prompt: str, width: int, height: int) -> GeneratedImage:
        # call your API here
        ...
```

2. Register it in `_build_service()` in `image_builder_tool.py`:

```python
elif provider == "myprovider":
    generator = MyProvider()
```

3. Set `IMAGE_PROVIDER=myprovider` at runtime.
