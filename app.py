"""
Uvicorn ASGI entrypoint: ``uvicorn app:app``.

Application composition lives in ``app_factory.create_app``. Run with::

    uvicorn app:app --reload --host 127.0.0.1 --port 8000

Prerequisites: ``.env`` for LLM keys; production UI build under ``frontend/dist/``.
Do not expose without TLS and access controls on public networks.
"""
from __future__ import annotations

from app_factory import create_app

app = create_app()
