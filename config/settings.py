"""
Single source of truth for Appeal Drafter AI.

All paths are under ``PROJECT_ROOT`` (the directory that contains ``app.py`` and this
``config`` package). Operational overrides come from environment variables — use
``.env`` at project root (see ``.env.example``); never commit secrets.

**Execution when this module loads:** Step 0 → Step N top to bottom (import-time only).
"""
from __future__ import annotations

import os
from pathlib import Path

# --- Step 0: resolve project root ---

_CONFIG_DIR = Path(__file__).resolve().parent
PROJECT_ROOT: Path = _CONFIG_DIR.parent

# --- Step 1: core directory layout ---

DATA_DIR = PROJECT_ROOT / "data"
PAYOR_FORMS_DIR = PROJECT_ROOT / "payor_standard_appeal_forms"
LOGS_DIR = PROJECT_ROOT / "logs"

# --- Step 2: knowledge base paths ---

KB_DIR = PROJECT_ROOT / "knowledge_base"
CURATED_DIR = KB_DIR / "curated"
PAYORS_DIR = CURATED_DIR / "payors"
GUIDELINES_DIR = CURATED_DIR / "guidelines"
DENIAL_CATEGORIES_DIR = CURATED_DIR / "denial_categories"
SOURCES_FILE = KB_DIR / "sources.txt"

# --- Step 3: Chroma / RAG defaults ---

CHROMA_PERSIST_DIR = PROJECT_ROOT / "chroma_db"
CHROMA_COLLECTION_NAME = "appeal_knowledge"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
# Tokenizer-based ingest chunking (preferred). Falls back to legacy names for compatibility.
CHUNK_TOKEN_SIZE = int(os.getenv("CHUNK_TOKEN_SIZE", os.getenv("CHUNK_SIZE", "256")))
CHUNK_TOKEN_OVERLAP = int(os.getenv("CHUNK_TOKEN_OVERLAP", os.getenv("CHUNK_OVERLAP", "32")))
EMBEDDING_BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", "64"))
TOP_K = 8

# --- Step 4: prompt and field truncation (from environment) ---

MAX_DENIAL_REASON_CHARS = int(os.getenv("MAX_DENIAL_REASON_CHARS", "8000"))
MAX_FIELD_CHARS = int(os.getenv("MAX_FIELD_CHARS", "2000"))

# --- Step 5: log rotation (from environment) ---

LOG_MAX_BYTES = int(os.getenv("LOG_MAX_BYTES", str(10 * 1024 * 1024)))
LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "5"))


def _parse_ingest_url_host_allowlist_from_env() -> frozenset[str]:
    """Build a lowercase hostname set from comma-separated ``INGEST_URL_HOST_ALLOWLIST``."""
    normalized_hosts: list[str] = []
    env_value = os.getenv("INGEST_URL_HOST_ALLOWLIST") or ""
    for raw_fragment in env_value.split(","):
        host_entry = raw_fragment.strip()
        if host_entry:
            normalized_hosts.append(host_entry.lower())
    return frozenset(normalized_hosts)


# --- Step 6: ingest URL allowlist (optional SSRF defense helper for ``knowledge_base.ingest``) ---

INGEST_URL_HOST_ALLOWLIST = _parse_ingest_url_host_allowlist_from_env()

# --- Step 7: knowledge-base URL fetch (ingest HTTP client) ---

INGEST_URL_REQUEST_TIMEOUT_SECONDS = float(os.getenv("INGEST_URL_REQUEST_TIMEOUT_SECONDS", "20"))

# --- Step 8: LLM client timeout ---

LLM_REQUEST_TIMEOUT_SECONDS = float(os.getenv("LLM_REQUEST_TIMEOUT_SECONDS", "120"))
