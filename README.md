# Appeal Drafter AI (MVP)

Real-time healthcare denial appeal letter drafter. Enter claim and denial details; the app drafts a formal appeal letter using an LLM and optional denial knowledge base.

## Setup

1. **Python 3.10+** recommended.

2. **Install dependencies (production / reproducible):**
   ```bash
   cd appeal_ai
   pip install -r requirements-lock.txt
   ```
   For local development tooling (pytest, pip-audit, pip-compile):
   ```bash
   pip install -r requirements-dev.txt
   ```
   To work from **floating** ranges instead (not recommended for prod deploys):
   `pip install -r requirements.txt`

3. **Web UI (React + Vite + MUI):** Node.js **20+** recommended (LTS). Install and build once so FastAPI can serve the SPA:
   ```bash
   cd frontend
   npm install
   npm run build
   cd ..
   ```
   Output is written to `frontend/dist/`.

4. **API key:** Copy `.env.example` to `.env` and set your LLM provider and key:
   ```bash
   copy .env.example .env
   # Edit .env: set LLM_PROVIDER=gemini or openai, then set GEMINI_API_KEY or OPENAI_API_KEY
   ```
   **Switching LLMs:** Set `LLM_PROVIDER=gemini` or `LLM_PROVIDER=openai` in `.env`. Optionally set `GEMINI_MODEL` or `OPENAI_MODEL`. No code changes needed.

5. **Run the app (API + built React UI on one port):**
   ```bash
   uvicorn app:app --reload --host 127.0.0.1 --port 8000
   ```

6. Open http://127.0.0.1:8000/ . Fill in the claim fields and click **Generate Appeal Letter** (the UI POSTs JSON to `/api/v1/appeal/draft`). API docs: http://127.0.0.1:8000/docs .

### React dev server (Vite HMR)

Use two terminals: **(1)** `uvicorn app:app --reload --host 127.0.0.1 --port 8000` **(2)** `cd frontend && npm run dev` — open the URL Vite prints (default http://127.0.0.1:5173/ ). `/api`, `/health`, `/docs`, etc. are proxied to port 8000 in `frontend/vite.config.ts`.

## MCP (Cursor / Claude Desktop)

Expose the same drafting pipeline to an MCP client:

```bash
python -m mcp_server
```

Setup and Cursor configuration: **`docs/MCP.md`**. Logs use **stderr** + `logs/appeal_drafter.log` so stdout stays clean for MCP.

## Data (optional)

- **`data/denial_knowledge_base - Main.csv`** — Denial code → category, appeal strategy, required documents, payer notes. Used for exact denial-code lookup (CO/remark codes).
- **Payor forms:** `payor_standard_appeal_forms/<PayorName>/appeal_form.txt` (and optionally `reconsideration_form.txt`) with placeholders like `{{APPEAL_BODY}}`, `{{PATIENT_NAME}}`, etc.

If the CSV is present, its content is used to improve the prompt. The app works without it.

## Knowledge base (RAG, policy-backed appeals)

The app can use a **local vector knowledge base** so appeals reference real policies and guidelines. All tools are **free** (no Firecrawl, no paid embeddings).

### What it does

- **Curated content**: Markdown files under `knowledge_base/curated/` (payors, guidelines, denial categories) are chunked, embedded with **sentence-transformers** (local), and stored in **Chroma** (local).
- At appeal time, the app retrieves relevant chunks by payer, denial code, CPT, and denial reason and adds them to the prompt.
- Result: policy-backed appeal text alongside your existing CSV guidance.

### Build the index (first time and after adding content)

From the project root (`appeal_ai`):

```bash
python -m knowledge_base.ingest
```

To also fetch optional URLs listed in `knowledge_base/sources.txt` (using Trafilatura, no API key):

```bash
python -m knowledge_base.ingest --urls
```

### Add more content

- **Payors:** Add `knowledge_base/curated/payors/<PayorName>.md` with appeal process, timelines, what to include.
- **Guidelines:** Add `knowledge_base/curated/guidelines/*.md` (e.g. CMS coverage, CPT documentation, medical necessity).
- **Denial categories:** Add `knowledge_base/curated/denial_categories/*.md`.
- Re-run `python -m knowledge_base.ingest` to refresh the index.

See **`docs/KNOWLEDGE_BASE_IMPLEMENTATION_PLAN.md`** for the full architecture and free-tools strategy.

## Project layout

```
appeal_ai/
  app.py                    # ASGI entry (uvicorn app:app)
  app_factory.py            # create_app(): compose FastAPI + static UI
  api/                      # REST schemas and routers
  frontend/                 # React + Vite + MUI (`npm run build` → dist/)
  .env                      # Local secrets (gitignored); copy from .env.example
  config/
    settings.py             # All paths, env-driven limits, KB + Chroma + LLM
    logging.py              # configure_logging, get_logger
  services/
    appeal_pipeline.py      # End-to-end draft orchestration
  llm_client.py             # OpenAI / Gemini facade
  prompt_template.py        # Appeal letter prompt
  utils/
    correlation.py          # X-Correlation-ID parsing + request.state helpers
    data_loader.py          # CSV denial KB
    form_loader.py          # Payor standard forms
    sanitize.py             # Prompt + log redaction
    e2e_step.py             # [E2E] timed step logging
  knowledge_base/           # RAG only (no separate config file)
    ingest.py, retrieve.py
    curated/, sources.txt
  mcp_server/               # MCP stdio server (python -m mcp_server)
  data/                     # denial_knowledge_base - Main.csv
  payor_standard_appeal_forms/
  chroma_db/                # Vector index (from ingest)
  docs/
  requirements.txt          # Semver ranges (source for pip-compile)
  requirements-lock.txt     # Pinned transitive deps (production installs)
  requirements-dev.txt      # pytest, pip-audit, pip-tools (after lock)
  .env.example
```

## Future enhancements (ideas)

- Bulk appeal generation from a spreadsheet
- More payors and denial categories in curated KB
- Optional scheduled ingest (e.g. refresh from sources.txt weekly)
- Optional local LLM (e.g. Ollama) alongside OpenAI
