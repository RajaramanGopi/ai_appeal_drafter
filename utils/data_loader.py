"""
Load the denial knowledge base (Main CSV) and look up guidance by denial code.

Denial codes from the UI:
- CO + number (e.g. CO97): EOB CODE "CO" and CLAIM ADJUSTMENT REASON CODE "97"
- Remark code (e.g. N362): REMITTANCE ADVICE REMARK CODE match

Matched rows are formatted for injection into the appeal prompt.

**Read order matches ``services.appeal_pipeline.build_denial_guidance_context``:**
first ``load_denial_knowledge_base``, then ``get_denial_knowledge_base_context``,
with helpers for each placed immediately after the function that calls them (depth-first).
"""
from __future__ import annotations

import re

import pandas as pd

from config.logging import get_logger
from config.settings import DATA_DIR
from utils.e2e_step import e2e_step, preview_text
from utils.error_support import (
    RESOLUTION_DENIAL_CSV_LOAD_FAILED,
    RESOLUTION_DENIAL_CSV_MISSING,
    format_resolution_for_log,
)

logger = get_logger("utils.data_loader")

_DENIAL_KB_MAIN = DATA_DIR / "denial_knowledge_base - Main.csv"

COLUMN_EOB_CODE = "EOB CODE"
COLUMN_CLAIM_ADJUSTMENT_REASON_CODE = "CLAIM ADJUSTMENT REASON CODE"
COLUMN_ADJUSTMENT_REASON_CODE_DESCRIPTION = "ADJUSTMENT REASON CODE DESCRIPTION"
COLUMN_REMITTANCE_ADVICE_REMARK_CODE = "REMITTANCE ADVICE REMARK CODE"
COLUMN_REMARK_CODE_DESCRIPTION = "REMARK CODE DESCRIPTION"
COLUMN_CATEGORY = "Category"
COLUMN_APPEAL_STRATEGY = "Appeal_Strategy"
COLUMN_MEDICAL_DOCUMENTS_REQUIRED = "Medical Documents Required as an attachment"
COLUMN_APPEAL_TEMPLATE = "Appeal Template to be used"
COLUMN_PAYER_NOTES = "Payer_Notes and Guidliens to be noted"


# --- Step 1: load CSV from disk (first call inside ``build_denial_guidance_context``) ---


def load_denial_knowledge_base() -> pd.DataFrame | None:
    """
    Load the denial knowledge base CSV from ``data/denial_knowledge_base - Main.csv``.

    Returns
    -------
    pandas.DataFrame or None
        Normalized column names on success; ``None`` if the file is missing or unreadable.

    Notes
    -----
    Side effects: disk read only. Logs row/column counts, not cell contents.
    """
    path = _DENIAL_KB_MAIN
    with e2e_step(logger, "utils.data_loader.load_denial_knowledge_base", csv_path=str(path)) as step_trace:
        if not path.is_file():
            logger.warning(
                "Denial knowledge CSV not found at %s. action=%s",
                path,
                format_resolution_for_log(RESOLUTION_DENIAL_CSV_MISSING),
            )
            step_trace.add(result="file_not_found")
            return None
        try:
            kb = pd.read_csv(path, encoding="utf-8", encoding_errors="replace")
            kb = _normalize_column_names(kb)
            step_trace.add(
                result="loaded",
                row_count=len(kb),
                column_count=len(kb.columns),
                column_names_preview=preview_text(", ".join(map(str, kb.columns)), 200),
            )
            logger.info(
                "Denial knowledge CSV loaded for appeal pipeline: path=%s rows=%d columns=%d",
                path,
                len(kb),
                len(kb.columns),
            )
            return kb
        except Exception:
            logger.exception(
                "load_denial_knowledge_base failed path=%s action=%s",
                path,
                format_resolution_for_log(RESOLUTION_DENIAL_CSV_LOAD_FAILED),
            )
            step_trace.add(result="read_error")
            return None


def _normalize_column_names(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Strip CSV column headers; called from ``load_denial_knowledge_base`` only."""
    if dataframe is None or dataframe.columns is None:
        return dataframe
    dataframe = dataframe.copy()
    dataframe.columns = [str(column_name).strip() for column_name in dataframe.columns]
    return dataframe


# --- Step 2: build CSV guidance string (second call in ``build_denial_guidance_context``) ---


def get_denial_knowledge_base_context(
    denial_knowledge_base: pd.DataFrame | None,
    denial_code: str | None = None,
    denial_reason: str | None = None,
) -> str:
    """
    Build guidance text for the LLM from the denial code and loaded CSV rows.

    Parameters
    ----------
    denial_knowledge_base :
        Data frame from ``load_denial_knowledge_base``, or ``None``.
    denial_code :
        UI denial code (e.g. ``CO97``, ``N362``). Parsed into CO/adjustment or remark.
    denial_reason :
        Reserved for future keyword expansion; currently ignored (not logged).

    Returns
    -------
    str
        Formatted guidance blocks joined by separators, or empty string if no match.

    Notes
    -----
    On unexpected errors during row filtering, logs exception and returns ``""``.
    """
    _ = denial_reason  # Reserved for future keyword expansion; kept for a stable public API.
    with e2e_step(
        logger,
        "utils.data_loader.get_denial_knowledge_base_context",
        denial_code_input=denial_code or "",
    ) as step_trace:
        if denial_knowledge_base is None or denial_knowledge_base.empty:
            step_trace.add(result="no_dataframe_or_empty")
            return ""

        eob_code, adjustment_reason_code, remark_code = _parse_denial_code_from_ui(denial_code)
        step_trace.add(
            parsed_eob=eob_code or "",
            parsed_adjustment_reason=adjustment_reason_code or "",
            parsed_remark_code=remark_code or "",
        )
        if not eob_code and not remark_code:
            step_trace.add(result="denial_code_unparseable")
            return ""

        columns_list = list(denial_knowledge_base.columns)
        col_map = {
            "adj_desc": _find_column(columns_list, [COLUMN_ADJUSTMENT_REASON_CODE_DESCRIPTION]),
            "remark_desc": _find_column(columns_list, [COLUMN_REMARK_CODE_DESCRIPTION]),
            "category": _find_column(columns_list, [COLUMN_CATEGORY]),
            "strategy": _find_column(columns_list, [COLUMN_APPEAL_STRATEGY]),
            "docs": _find_column(columns_list, [COLUMN_MEDICAL_DOCUMENTS_REQUIRED]),
            "template": _find_column(columns_list, [COLUMN_APPEAL_TEMPLATE]),
            "payer_notes": _find_column(columns_list, [COLUMN_PAYER_NOTES, "Payer_Notes"]),
            "_match_eob": eob_code,
            "_match_remark": remark_code,
        }

        try:
            matched = _rows_matching_denial_code(
                denial_knowledge_base, eob_code, adjustment_reason_code, remark_code
            )
        except (TypeError, ValueError, KeyError) as err:
            logger.exception("Row filter failed for denial_code=%s: %s", denial_code, err)
            step_trace.add(result="row_filter_error", error=type(err).__name__)
            return ""

        if matched.empty:
            step_trace.add(result="no_matching_rows", matched_row_count=0)
            return ""

        snippets: list[str] = []
        for _, row in matched.iterrows():
            text = _format_row_guidance(row, col_map)
            if text:
                snippets.append(text)

        if not snippets:
            step_trace.add(result="matched_rows_but_empty_snippets", matched_row_count=len(matched))
            return ""

        combined = "Relevant guidance from denial knowledge base:\n\n" + "\n\n---\n\n".join(snippets)
        step_trace.add(
            result="context_built",
            matched_row_count=len(matched),
            snippet_count=len(snippets),
            output_chars=len(combined),
            output_preview=preview_text(combined, 500),
        )
        return combined


def _parse_denial_code_from_ui(denial_code_input: str | None):
    """Parse UI denial code; first transformation inside ``get_denial_knowledge_base_context``."""
    if not denial_code_input or not str(denial_code_input).strip():
        return (None, None, None)
    raw = str(denial_code_input).strip().upper()
    raw_compact = re.sub(r"\s+", "", raw)
    co_match = re.match(r"^CO\s*(\d+)$", raw, re.IGNORECASE)
    if co_match:
        return ("CO", co_match.group(1).lstrip("0") or "0", None)
    if raw.isdigit():
        return ("CO", raw.lstrip("0") or "0", None)
    if raw_compact:
        return (None, None, raw_compact)
    return (None, None, None)


def _find_column(column_list: list, possible_names: list[str]) -> str | None:
    """Exact match on stripped, case-insensitive column names (no substring guessing)."""
    if not column_list:
        return None
    normalized_to_original = {str(column_name).strip().lower(): column_name for column_name in column_list}
    for name in possible_names:
        lookup_key = str(name).strip().lower()
        if lookup_key in normalized_to_original:
            return normalized_to_original[lookup_key]
    return None


def _cell_str(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value).strip()


def _rows_matching_denial_code(
    df: pd.DataFrame,
    eob_code: str | None,
    adjustment_reason_code: str | None,
    remark_code: str | None,
) -> pd.DataFrame:
    columns = list(df.columns)
    col_eob = _find_column(columns, [COLUMN_EOB_CODE])
    col_adj = _find_column(columns, [COLUMN_CLAIM_ADJUSTMENT_REASON_CODE])
    col_remark = _find_column(columns, [COLUMN_REMITTANCE_ADVICE_REMARK_CODE])

    if eob_code and adjustment_reason_code and col_eob and col_adj:
        series_eob = df[col_eob].map(_cell_str).str.upper()
        series_adj = df[col_adj].map(_cell_str).str.replace(r"\.0$", "", regex=True).str.strip()
        mask = (series_eob == "CO") & (series_adj == str(adjustment_reason_code))
        return df.loc[mask]

    if remark_code and col_remark:
        series_remark = df[col_remark].map(_cell_str).str.upper().str.replace(" ", "", regex=False)
        mask = series_remark == remark_code.upper()
        return df.loc[mask]

    return df.iloc[0:0]


def _format_row_guidance(row: pd.Series, columns: dict[str, str | None]) -> str | None:
    col_adj_desc = columns["adj_desc"]
    col_remark_desc = columns["remark_desc"]
    col_category = columns["category"]
    col_strategy = columns["strategy"]
    col_docs = columns["docs"]
    col_template = columns["template"]
    col_payer_notes = columns["payer_notes"]

    eob_code = columns.get("_match_eob")
    remark_code = columns.get("_match_remark")
    description_text = ""
    if eob_code and col_adj_desc:
        description_text = _cell_str(row.get(col_adj_desc))
    elif remark_code and col_remark_desc:
        description_text = _cell_str(row.get(col_remark_desc))

    parts: list[str] = []
    if description_text:
        parts.append(f"Denial description: {description_text}")
    if col_category and pd.notna(row.get(col_category)):
        parts.append(f"Category: {row[col_category]}")
    if col_strategy and pd.notna(row.get(col_strategy)):
        parts.append(f"Appeal strategy: {row[col_strategy]}")
    if col_docs and pd.notna(row.get(col_docs)):
        parts.append(f"Medical documents required: {row[col_docs]}")
    if col_template and pd.notna(row.get(col_template)):
        parts.append(f"Appeal template to use: {row[col_template]}")
    if col_payer_notes and pd.notna(row.get(col_payer_notes)):
        parts.append(f"Payer notes and guidelines: {row[col_payer_notes]}")

    if not parts:
        return None
    return "\n".join(parts)
