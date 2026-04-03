"""
Central configuration package.

- **settings** — paths, env-driven limits, knowledge-base layout, Chroma, ingest/LLM timeouts.
- **logging** — ``configure_logging``, ``get_logger``.

**Environment:** place ``.env`` next to ``app.py`` (project root). Copy from ``.env.example``.

**Layout (mental model)**

::

    project_root/
      app.py                 # ASGI entry: uvicorn app:app
      app_factory.py         # create_app(): middleware, API, static UI, error handlers
      requirements-lock.txt # pinned deps (no optional mcp / pywin32)
      requirements-mcp.txt  # optional MCP SDK (after lock)
      .env                   # local secrets (gitignored)
      config/                # this package — all knobs in settings.py
      services/              # orchestration (appeal pipeline)
      utils/                 # shared helpers (data, forms, sanitize, e2e logging)
      knowledge_base/        # RAG: ingest, retrieve, curated/, sources.txt
      data/                    # denial CSV
      payor_standard_appeal_forms/
      chroma_db/               # local vector store (often gitignored)
      logs/
"""
