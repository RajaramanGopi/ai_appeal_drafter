"""
Input shaping for LLM prompts and safe summaries for logs.

Truncation limits surface area for prompt injection and log volume.
``claim_data_for_log`` redacts fields that often contain PHI or sensitive text.

**Read order matches typical use:** pipeline uses ``sanitize_claim_data`` before the LLM;
``app.py`` logs with ``claim_data_for_log`` on button click.
"""
from __future__ import annotations

from typing import Any, Mapping

from config.logging import get_logger
from config.settings import MAX_DENIAL_REASON_CHARS, MAX_FIELD_CHARS
from utils.e2e_step import e2e_step

_logger = get_logger("utils.sanitize")


# --- Step 0: shared truncation (used by both public functions below) ---


def _truncate(value: Any, max_len: int) -> str:
    """Return stripped string text truncated to ``max_len`` (with ``...`` if cut)."""
    if value is None:
        return ""
    text = str(value).strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


# --- Step 1: LLM-facing field limits (used from ``run_appeal_draft`` → ``sanitize_claim_data``) ---


_LONG_TEXT_KEYS = frozenset({"denial_reason"})


def sanitize_claim_data(claim_data: Mapping[str, Any]) -> dict[str, Any]:
    """
    Return a shallow copy of ``claim_data`` with string fields truncated for LLM use.

    Parameters
    ----------
    claim_data :
        Raw claim fields from the UI or API.

    Returns
    -------
    dict
        Copy suitable for ``build_prompt`` / ``generate_appeal``. Long ``denial_reason``
        uses ``MAX_DENIAL_REASON_CHARS``; other strings use ``MAX_FIELD_CHARS``.
    """
    with e2e_step(_logger, "utils.sanitize.sanitize_claim_data") as step_trace:
        sanitized: dict[str, Any] = {}
        for key, raw in claim_data.items():
            if key in _LONG_TEXT_KEYS:
                sanitized[key] = _truncate(raw, MAX_DENIAL_REASON_CHARS)
            elif isinstance(raw, str):
                sanitized[key] = _truncate(raw, MAX_FIELD_CHARS)
            else:
                sanitized[key] = raw
        step_trace.add(
            input_field_count=len(claim_data),
            output_field_count=len(sanitized),
            denial_reason_truncated=bool(
                isinstance(claim_data.get("denial_reason"), str)
                and len(str(claim_data.get("denial_reason")).strip()) > MAX_DENIAL_REASON_CHARS
            ),
        )
        return sanitized


# --- Step 2: log-safe summary (used from ``app`` on generate; redacts sensitive keys) ---


_SENSITIVE_KEYS = frozenset(
    {
        "patient_name",
        "denial_reason",
        "provider",
        "payer",
    }
)


def claim_data_for_log(claim_data: Mapping[str, Any]) -> dict[str, Any]:
    """
    Build a log-safe summary: sensitive keys redacted, other strings shortened.

    Parameters
    ----------
    claim_data :
        Same shape as UI claim dict.

    Returns
    -------
    dict
        Safe to pass to ``logger.info`` for support/debugging (not for compliance
        attestation on its own).
    """
    summary: dict[str, Any] = {}
    for key, raw in claim_data.items():
        if key in _SENSITIVE_KEYS:
            if raw is None or (isinstance(raw, str) and not raw.strip()):
                summary[key] = None
            else:
                summary[key] = "[redacted]"
        elif isinstance(raw, str):
            summary[key] = _truncate(raw, 120)
        else:
            summary[key] = raw
    return summary
