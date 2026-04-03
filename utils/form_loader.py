"""
Load and fill payor-specific appeal forms from payor_standard_appeal_forms/.

Each payor has a folder (e.g. Aetna/) containing appeal_form.txt
(and optionally reconsideration_form.txt). Paths are resolved and confined
to the forms root directory to avoid path traversal.

**Read order matches Streamlit ``app.py`` top-to-bottom on each run:** shared path
helpers, sidebar discovery (``list_available_payors``), then — after generate —
``get_filled_form_for_payer`` → ``find_form_for_payer`` → ``fill_form``.
"""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from config.logging import get_logger
from config.settings import PAYOR_FORMS_DIR
from utils.e2e_step import e2e_step, preview_text

logger = get_logger("utils.form_loader")

_FORMS_ROOT = PAYOR_FORMS_DIR.resolve()

_STANDARD_FORM_FILENAMES = ("appeal_form.txt", "reconsideration_form.txt", "form.txt")


# --- Step 0: shared path + name normalization (used by discovery and match) ---


def _safe_child_path(parent: Path, *parts: str) -> Path | None:
    """Return resolved path only if it stays under parent (after resolve)."""
    try:
        candidate = (parent.joinpath(*parts)).resolve()
        candidate.relative_to(parent)
        return candidate
    except (ValueError, OSError):
        logger.warning("Rejected path outside forms root: %s under %s", parts, parent)
        return None


def _normalize_payer(payer_name: str) -> str:
    if not payer_name:
        return ""
    return " ".join(str(payer_name).strip().lower().split())


def _payer_match_key(payer_name: str) -> str:
    """Lowercase single-spaced name with spaces removed (e.g. United Healthcare → unitedhealthcare)."""
    return _normalize_payer(payer_name).replace(" ", "")


# --- Step 1: sidebar — list folders that contain a standard form file ---


def list_available_payors() -> list[str]:
    """
    List payor folder names under ``payor_standard_appeal_forms`` that include a form file.

    Returns
    -------
    list of str
        Sorted folder names. Empty if the root directory is missing or has no forms.
    """
    if not _FORMS_ROOT.is_dir():
        logger.info("Payor forms directory missing or not a directory: %s", _FORMS_ROOT)
        return []
    names: list[str] = []
    for entry in _FORMS_ROOT.iterdir():
        if not entry.is_dir():
            continue
        safe_dir = _safe_child_path(_FORMS_ROOT, entry.name)
        if safe_dir is None:
            continue
        if any(
            (safe_dir / standard_filename).is_file()
            for standard_filename in _STANDARD_FORM_FILENAMES
        ):
            names.append(entry.name)
    result = sorted(names)
    logger.info("Standard forms available for %s payor(s)", len(result))
    return result


# --- Step 2: pipeline — resolve template file for payer ---


def find_form_for_payer(
    payer_name: str, request_type: str = "appeal"
) -> tuple[str | None, str | None]:
    """
    Resolve a payor folder and read the best matching template file.

    Parameters
    ----------
    payer_name :
        User-entered payer label (matched case-insensitively to folder names).
    request_type :
        ``"appeal"`` or ``"reconsideration"`` to prefer different filenames.

    Returns
    -------
    tuple
        ``(folder_name, template_text)`` or ``(None, None)`` if none found.

    Notes
    -----
    Side effects: reads files only under the configured forms root (path-safe).
    """
    with e2e_step(
        logger,
        "utils.form_loader.find_form_for_payer",
        request_type=request_type,
        payer_query_nonempty=bool(payer_name and str(payer_name).strip()),
    ) as step_trace:
        if not payer_name or not _FORMS_ROOT.is_dir():
            step_trace.add(result="no_payer_or_root_missing")
            return None, None

        normalized_input = _normalize_payer(payer_name)
        if not normalized_input:
            step_trace.add(result="payer_normalizes_empty")
            return None, None

        input_key = _payer_match_key(payer_name)
        candidates: list[tuple[str, Path]] = []
        for entry in sorted(_FORMS_ROOT.iterdir()):
            if not entry.is_dir():
                continue
            safe_dir = _safe_child_path(_FORMS_ROOT, entry.name)
            if safe_dir is None:
                continue
            folder_norm = _normalize_payer(entry.name)
            folder_key = _payer_match_key(entry.name)
            if folder_key == input_key:
                candidates.insert(0, (entry.name, safe_dir))
                break
            if normalized_input in folder_norm or folder_norm in normalized_input:
                candidates.append((entry.name, safe_dir))

        if not candidates:
            step_trace.add(result="no_folder_match", candidate_folders_scanned="see_forms_root")
            return None, None

        matched_name, matched_dir = candidates[0]
        step_trace.add(matched_payor_folder=matched_name, candidate_count=len(candidates))
        if request_type == "reconsideration":
            form_order = ["reconsideration_form.txt", "appeal_form.txt", "form.txt"]
        else:
            form_order = list(_STANDARD_FORM_FILENAMES)

        for form_filename in form_order:
            form_path = _safe_child_path(matched_dir, form_filename)
            if form_path is None or not form_path.is_file():
                continue
            try:
                content = form_path.read_text(encoding="utf-8", errors="replace")
                step_trace.add(
                    result="template_loaded",
                    form_file=form_filename,
                    template_chars=len(content),
                    template_preview=preview_text(content, 300),
                )
                return matched_name, content
            except OSError as err:
                logger.warning(
                    "Could not read form file %s: %s. action=Verify the file exists, is UTF-8 text, "
                    "and the process has read permission.",
                    form_path,
                    err,
                )

        step_trace.add(result="no_readable_form_file", matched_payor_folder=matched_name)
        return None, None


# --- Step 3: pipeline — substitute placeholders ---


def fill_form(
    template_content: str,
    claim_data: dict,
    appeal_body: str,
    request_date: str | None = None,
) -> str:
    """
    Replace ``{{PLACEHOLDER}}`` keys in a template; unknown keys removed.

    Parameters
    ----------
    template_content :
        Raw template text from disk.
    claim_data :
        Dict with patient, payer, codes, denial_reason, etc.
    appeal_body :
        LLM output inserted for ``APPEAL_BODY``.
    request_date :
        Optional ``YYYY-MM-DD``; defaults to today (local date).

    Returns
    -------
    str
        Filled template text.

    Notes
    -----
    Pure string substitution; no I/O.
    """
    with e2e_step(
        logger,
        "utils.form_loader.fill_form",
        template_chars=len(template_content or ""),
        appeal_body_chars=len(appeal_body or ""),
    ) as step_trace:
        if request_date is None:
            request_date = date.today().strftime("%Y-%m-%d")
        replacements = {
            "PATIENT_NAME": claim_data.get("patient_name") or "N/A",
            "DATE_OF_SERVICE": claim_data.get("dos") or "N/A",
            "PROVIDER_NAME": claim_data.get("provider") or "N/A",
            "PAYER_NAME": claim_data.get("payer") or "N/A",
            "DENIAL_CODE": claim_data.get("denial_code") or "N/A",
            "CPT_CODE": claim_data.get("cpt_code") or "N/A",
            "ICD_CODE": claim_data.get("icd_code") or "N/A",
            "DENIAL_REASON": claim_data.get("denial_reason") or "N/A",
            "REQUEST_DATE": request_date,
            "APPEAL_BODY": appeal_body or "",
        }
        filled = template_content
        for key, value in replacements.items():
            filled = filled.replace("{{" + key + "}}", str(value))
        filled = re.sub(r"\{\{[^}]+\}\}", "", filled)
        step_trace.add(filled_chars=len(filled), placeholder_keys=len(replacements))
        return filled


# --- Step 4: pipeline — orchestrate find + fill (called from ``run_appeal_draft``) ---


def get_filled_form_for_payer(
    payer_name: str,
    claim_data: dict,
    appeal_body: str,
    request_type: str = "appeal",
) -> tuple[str | None, str | None]:
    """
    Locate a payor template and fill it with ``claim_data`` and ``appeal_body``.

    Returns
    -------
    tuple
        ``(filled_text, matched_payor_name)`` or ``(None, None)`` if no template.
    """
    with e2e_step(
        logger,
        "utils.form_loader.get_filled_form_for_payer",
        request_type=request_type,
        payer_query_nonempty=bool(payer_name and str(payer_name).strip()),
    ) as step_trace:
        matched_name, template = find_form_for_payer(payer_name, request_type=request_type)
        if not template:
            step_trace.add(result="no_template_for_payer")
            return None, None
        filled = fill_form(template, claim_data, appeal_body)
        step_trace.add(
            result="filled",
            matched_payor_folder=matched_name,
            filled_form_chars=len(filled),
        )
        return filled, matched_name
