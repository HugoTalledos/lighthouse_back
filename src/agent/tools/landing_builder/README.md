# Lighthouse Back — landing_builder Tool

Pair of LangGraph tools that generate a static Astro landing page from a business brief, deploy it to a Firebase Hosting preview channel so the frontend can show a live preview, and — only once the user approves that preview — persist the approved version's source as a versioned snapshot in Firebase Storage.

The LLM never writes HTML/CSS/JS: it composes the page as a structured sequence of sections chosen from a fixed library (`hero`, `features`, `capture`, `testimonials`, `pricing`, `faq`, `cta`, `footer`) defined by an Astro template hosted in a separate, public GitHub repo. That library isn't hardcoded here — it's fetched at build time from the template's `.agent/page.schema.json` (structured-output schema) and `.agent/PAGE_JSON.md` (prompt guidance), so a template-side schema change never requires a `lighthouse_back` code change.

v1 scope is initial generation only — no follow-up editing of an already-generated landing.

---

## Requirements

- Python 3.9+
- Node.js/`npm`/`npx` available on `PATH` (used to `npm install && astro build` the template)
- An OpenRouter API key (or set provider `ollama` for this tool in `config/llm.{APP_ENV}.json` to run against a local Ollama server)
- A public GitHub repo hosting the Astro template (`LANDING_TEMPLATE_REPO`)
- A Firebase project with Hosting and Storage enabled

---

## Installation

```bash
pip install -r requirements.txt
```

---

## Configuration

| Variable | Required | Default | Description |
|---|---|---|---|
| `LANDING_TEMPLATE_REPO` | Yes | — | `owner/repo` of the public Astro template |
| `LANDING_TEMPLATE_REF` | No | `main` | Branch/tag/commit to fetch |
| `LANDING_BUILD_TIMEOUT_SECONDS` | No | `180` | Max seconds for `npm install && astro build` |
| `FIREBASE_HOSTING_SITE_ID` | Yes | — | Firebase Hosting site id to deploy preview channels to |
| `FIREBASE_STORAGE_BUCKET` | Yes | — | Reused for `landings/` snapshots |
| `GOOGLE_APPLICATION_CREDENTIALS` | No | — | Firebase/Hosting auth (ADC if omitted) |
| `OPENROUTER_API_KEY` | Yes (when this tool's provider is `openrouter`) | — | OpenRouter API key |
| `OLLAMA_BASE_URL` | No | `http://localhost:11434` | Ollama server URL (when this tool's provider is `ollama`) |

Provider and model for this tool are set in `config/llm.{APP_ENV}.json` (see
`CLAUDE.md`'s "Configuración de LLM" section), not via env vars.

---

## Usage

```python
from src.agent.tools.landing_builder.landing_builder_tool import landing_builder_tool
from src.agent.tools.landing_builder.promote_landing_tool import promote_landing_tool

brief_dict = {
    "project_id": "acme-launch-001",
    "business_name": "Acme Co",
    "value_proposition": "Saves you 10 hours a week on invoicing",
    "target_customer": "Freelancers and small business owners",
    "product_or_service": "Invoicing SaaS",
    "tone_hint": "playful",
    "primary_cta_goal": "collect emails",
    "brand_color_hint": "#FF5733",
}

# 1. Generate + deploy a preview. Nothing is persisted yet.
build_result = await landing_builder_tool.ainvoke({"brief_dict": brief_dict})
print(build_result["status"])       # "success" | "failed"
print(build_result["preview_url"])  # live Firebase Hosting preview URL, or None on failure

# 2. Surface preview_url to the user. Re-running landing_builder_tool with a
#    tweaked brief redeploys the *same* preview channel (stable URL).

# 3. Once the user approves, persist the exact approved composition:
promote_result = await promote_landing_tool.ainvoke({
    "project_id": brief_dict["project_id"],
    "composition_dict": build_result["composition"],
})
print(promote_result["status"])       # "success" | "failed"
print(promote_result["storage_path"]) # e.g. "landings/acme-launch-001/20260710T120000Z/source.tar.gz"
```

---

## Architecture

```
src/agent/tools/landing_builder/
├── domain/
│   ├── models.py               # LandingBrief, LandingBuildResult (composition: dict), LandingPromoteResult
│   ├── ports.py                # TemplateSourcePort, StaticBuilderPort, HostingPort, LandingStoragePort
│   └── prompt_builder.py       # build_landing_prompt(brief, page_json_doc) -> (system, user)
├── application/
│   ├── agent_docs.py                  # read_page_json_doc/read_page_schema from the fetched template's .agent/
│   ├── page_renderer.py               # render(composition: dict, project_dir) — deterministic, no LLM
│   ├── landing_builder_service.py     # build(brief) -> LandingBuildResult
│   └── landing_promotion_service.py   # promote(project_id, composition: dict) -> LandingPromoteResult
├── infrastructure/
│   ├── github_template_fetcher.py     # GithubTemplateFetcher (TemplateSourcePort)
│   ├── astro_builder.py               # AstroNodeBuilder (StaticBuilderPort)
│   ├── firebase_hosting_deployer.py   # FirebaseHostingDeployer (HostingPort)
│   └── landing_storage.py             # FirebaseLandingStorage (LandingStoragePort)
├── landing_builder_tool.py     # @tool landing_builder_tool + _build_service()
└── promote_landing_tool.py     # @tool promote_landing_tool + _build_promotion_service()
```

Pipeline:

```
landing_builder_tool(brief)
  fetch template (GitHub, public, ephemeral temp dir)
    → read .agent/PAGE_JSON.md + .agent/page.schema.json from the fetched template
    → LLM generate_structured_from_schema → dict, validated against page.schema.json
    → render composition into template (src/data/page.json)
    → astro build (subprocess)
    → deploy dist/ to Firebase Hosting preview channel (channel_id = project_id)
  returns { composition, preview_url, status, errors }   ← nothing persisted

promote_landing_tool(project_id, composition)             ← call only after user approval
  fetch template again (fresh temp dir)
    → render same composition
    → tar source (excluding node_modules/.git/dist)
    → upload to Storage: landings/{project_id}/{version}/source.tar.gz
  returns { version, storage_path, status, errors }
```

---

## Running tests

```bash
python3 -m pytest tests/test_landing_builder_tool.py tests/test_promote_landing_tool.py \
  tests/unit/domain/test_landing_models.py tests/unit/domain/test_landing_prompt_builder.py \
  tests/unit/application/test_page_renderer.py tests/unit/application/test_landing_builder_service.py \
  tests/unit/application/test_landing_promotion_service.py \
  tests/unit/infrastructure/test_github_template_fetcher.py tests/unit/infrastructure/test_astro_builder.py \
  tests/unit/infrastructure/test_firebase_hosting_deployer.py tests/unit/infrastructure/test_landing_storage.py \
  -v
```

Note: running the full suite via `python3 -m pytest -v` will currently also surface unrelated pre-existing collection errors from `image_builder`/`campaign_builder` test files importing a stale `src.agent.<tool>` path instead of `src.agent.tools.<tool>` — that predates and is unrelated to `landing_builder`.

---

## Out of scope (v1)

- Editing an already-generated landing.
- Publishing to a permanent Hosting site/domain (only source snapshots are persisted).
- Free-form code editing by the LLM — it only composes over the fixed section library.
- Real generated images for sections (`image_url` is a plain string or `None`; no `image_builder` integration yet).
- A dedicated GitHub repo per landing, or TTL/lifecycle on the `landings/` Storage prefix.
- `node_modules` caching between builds.
