"""
Shared operational messages for logs and UI when something fails.

Keep text free of PHI; use for **what failed**, **where to look**, and **next steps**.
"""
from __future__ import annotations

# --- CSV denial knowledge ---
RESOLUTION_DENIAL_CSV_MISSING = (
    "Verify `data/denial_knowledge_base - Main.csv` exists at the project root and is readable.",
    "Confirm the file is valid UTF-8 CSV and column headers match the template (see data_loader column constants).",
)

RESOLUTION_DENIAL_CSV_LOAD_FAILED = (
    "Open `logs/appeal_drafter.log` for the full traceback.",
    "Re-export the CSV from your source tool; avoid merged cells or corrupt rows.",
)

# --- Chroma / RAG ---
RESOLUTION_CHROMA_UNAVAILABLE = (
    "If you use RAG, run `python -m knowledge_base.ingest` (add `--urls` only if sources.txt is curated).",
    "Install optional deps: `pip install chromadb sentence-transformers` if imports fail.",
)

RESOLUTION_CHROMA_QUERY_FAILED = (
    "Delete folder `chroma_db` and re-run `python -m knowledge_base.ingest` to rebuild the index.",
    "Ensure no other process has the Chroma database locked (close duplicate Streamlit runs).",
)

RESOLUTION_EMBEDDING_MODEL_FAILED = (
    "First embedding load downloads `all-MiniLM-L6-v2` (~80MB); ensure network access or set offline cache.",
    "Optional: set `HF_TOKEN` in `.env` (read token from https://huggingface.co/settings/tokens) for higher Hub rate limits.",
    "If disk is full or antivirus blocks the cache, free space or allow the Hugging Face / torch cache directory.",
)

# --- LLM configuration ---
RESOLUTION_LLM_NOT_CONFIGURED = (
    "Set `LLM_PROVIDER` to `openai` or `gemini` in `.env` (see `.env.example`).",
    "Set `OPENAI_API_KEY` or `GEMINI_API_KEY` / `GOOGLE_API_KEY` for the chosen provider.",
)

RESOLUTION_LLM_AUTH = (
    "Confirm the API key in `.env` matches the provider dashboard (no extra spaces or quotes).",
    "Regenerate the key if it was rotated or revoked.",
)

RESOLUTION_LLM_RATE_LIMIT = (
    "Wait briefly and retry; check provider quota and billing on the vendor console.",
    "Consider switching `LLM_PROVIDER` or using a smaller model via `OPENAI_MODEL` / `GEMINI_MODEL`.",
)

RESOLUTION_LLM_TIMEOUT = (
    "Increase `LLM_REQUEST_TIMEOUT_SECONDS` in `.env` (see `config.settings`).",
    "Retry when the network is stable; large prompts with RAG take longer.",
)

RESOLUTION_LLM_NETWORK = (
    "Check internet connectivity, VPN, and corporate firewall rules for the LLM API host.",
    "Retry after a transient outage; if behind a proxy, configure system/proxy env vars for Python.",
)

RESOLUTION_EMPTY_LLM_OUTPUT = (
    "Retry generation once; empty responses can be transient under provider load.",
    "If it repeats, try another `GEMINI_MODEL` / `OPENAI_MODEL` or set `LLM_PROVIDER` to the other vendor.",
    "Shorten optional RAG context by rebuilding a smaller Chroma index or clearing `chroma_db` temporarily.",
)

RESOLUTION_GEMINI_BLOCKED_OR_EMPTY = (
    "If content was blocked, shorten or generalize free-text fields (denial reason) and retry.",
    "Confirm `GEMINI_MODEL` is a valid model ID for your API key; try `gemini-2.0-flash` or `gemini-1.5-flash`.",
    "As a fallback, set `LLM_PROVIDER=openai` with a valid `OPENAI_API_KEY`.",
)

RESOLUTION_OPENAI_BAD_REQUEST = (
    "Verify `OPENAI_MODEL` exists for your account (see OpenAI model list).",
    "Reduce prompt size: shorten denial reason or disable RAG temporarily by removing `chroma_db` if corrupted.",
)

# --- Generic pipeline / UI ---
RESOLUTION_UNEXPECTED_PIPELINE = (
    "Open `logs/appeal_drafter.log` and search for the correlation_id from this session.",
    "Re-run with the same inputs after `pip install -r requirements.txt` to rule out missing packages.",
    "If the error mentions a specific module, share that traceback with your support contact (no PHI).",
)


def format_resolution_for_log(steps: tuple[str, ...]) -> str:
    """Single-line summary for structured logs."""
    if not steps:
        return ""
    return " | ".join(steps)
