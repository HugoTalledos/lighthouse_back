# Lighthouse Back — campaign_builder Tool

LangGraph tool that generates a Facebook Marketing API campaign configuration (Campaign → AdSet → Ad) from a business brief. Uses an LLM to infer objective, targeting, placements, ad copy, and budget. Does **not** publish to Facebook.

---

## Requirements

- Python 3.9+
- An OpenRouter API key (or set provider `ollama` for this tool in `config/llm.{APP_ENV}.json` to run against a local Ollama server)

---

## Installation

```bash
pip install -r requirements.txt
```

---

## Configuration

Provider and model for this tool are set in `config/llm.{APP_ENV}.json` (see
`CLAUDE.md`'s "Configuración de LLM" section), not via env vars.

| Variable | Required | Default | Description |
|---|---|---|---|
| `OPENROUTER_API_KEY` | Yes (when this tool's provider is `openrouter`) | — | OpenRouter API key |
| `OLLAMA_BASE_URL` | No | `http://localhost:11434` | Ollama server URL (when this tool's provider is `ollama`) |

---

## Usage

```python
from src.agent.tools.campaign_builder.campaign_builder_tool import campaign_builder_tool

brief_dict = {
    "project_id": "my-campaign-001",
    "business_name": "Acme Co",
    "value_proposition": "Saves you 10 hours a week on invoicing",
    "target_customer": "Freelancers and small business owners",
    "product_or_service": "Invoicing SaaS",
    "approx_daily_budget_usd": 10.0,
    "country": "MX",
    "goal_hint": "Drive free trial sign-ups",
}

# Inside an async context / LangGraph node:
result = await campaign_builder_tool.ainvoke({"brief_dict": brief_dict})

print(result["status"])   # "success" | "failed"
print(result["errors"])   # list of error messages if any
print(result["campaign"]) # full Campaign dict, or None on failure
```

---

## Output format

```json
{
  "status": "success",
  "errors": [],
  "brief": { "...": "..." },
  "campaign": {
    "name": "Acme Free Trial Campaign",
    "objective": "OUTCOME_LEADS",
    "status": "PAUSED",
    "special_ad_categories": [],
    "ad_sets": [
      {
        "name": "Freelancers MX",
        "daily_budget_usd": 10.0,
        "billing_event": "IMPRESSIONS",
        "optimization_goal": "LEAD_GENERATION",
        "targeting": {
          "countries": ["MX"],
          "age_min": 22,
          "age_max": 45,
          "genders": ["ALL"],
          "interests": ["freelancing", "productivity"]
        },
        "placements": {
          "publisher_platforms": ["facebook", "instagram"],
          "facebook_positions": ["feed"],
          "instagram_positions": ["stream", "story"]
        },
        "duration_days": 14,
        "ads": [
          {
            "name": "Ad 1 — Save time",
            "creative": {
              "primary_text": "Stop chasing invoices. Acme handles it in seconds.",
              "headline": "Reclaim your week",
              "description": null,
              "call_to_action": "SIGN_UP",
              "link_url": null
            }
          }
        ]
      }
    ]
  }
}
```

---

## Architecture

```
src/agent/campaign_builder/
├── domain/
│   ├── models.py            # CampaignBrief, enums, Campaign→AdSet→Ad, CampaignConfigResult
│   └── prompt_builder.py    # build_campaign_prompt(brief) → (system, user)
├── application/
│   └── campaign_builder_service.py  # Calls LLM, isolates failures into errors
└── campaign_builder_tool.py # @tool entry point

src/shared/llm/              # Provider-agnostic LLM kernel
├── domain/
│   ├── models.py            # LLMMessage, Role, LLMResponse
│   └── ports.py             # LLMClientPort ABC
├── infrastructure/
│   ├── openrouter_client.py    # OpenRouter chat/completions via httpx (no SDK)
│   └── ollama_local_client.py  # Local Ollama server via httpx
└── factory.py               # build_llm_client(settings) → LLMClientPort per config/llm.{APP_ENV}.json
```

---

## Running tests

```bash
python3 -m pytest -v
```

---

## Adding a new LLM provider

1. Create `src/shared/llm/infrastructure/my_provider.py` implementing `LLMClientPort`:

```python
from src.shared.llm.domain.ports import LLMClientPort

class MyProvider(LLMClientPort):
    async def complete(self, prompt, *, system=None, temperature=0.7):
        # call your API here
        ...

    async def generate_structured(self, prompt, response_model, *, system=None, temperature=0.4):
        # call your API here
        ...
```

2. Register it in `_CLIENTS` in `src/shared/llm/factory.py`.

3. Agregar `myprovider` al `Literal` de `Provider` en `src/shared/llm_config/domain/models.py` y usarlo en `config/llm.*.json`.
