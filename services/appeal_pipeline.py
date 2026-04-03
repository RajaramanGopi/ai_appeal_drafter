"""
End-to-end appeal drafting: optional CSV + RAG guidance, LLM draft, optional payor form.

``llm_client.generate_appeal`` is the only LLM entry point (provider selection + API call);
this module orchestrates sanitization, guidance, that call, and payor form fill. It does
not duplicate the LLM logic.

The FastAPI layer in ``app.py`` / ``api/routes.py`` calls this module; it stays testable without the web stack.

**Read order matches ``run_appeal_draft()``:** result type, orchestrator body line-by-line,
then ``build_denial_guidance_context`` (the subroutine invoked mid-body).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from config.logging import get_logger
from llm_client import generate_appeal, LLMError
from utils.error_support import (
    RESOLUTION_CHROMA_UNAVAILABLE,
    RESOLUTION_CHROMA_QUERY_FAILED,
    RESOLUTION_DENIAL_CSV_LOAD_FAILED,
    RESOLUTION_EMPTY_LLM_OUTPUT,
    format_resolution_for_log,
)
from utils.data_loader import load_denial_knowledge_base, get_denial_knowledge_base_context
from utils.e2e_step import e2e_step
from utils.form_loader import get_filled_form_for_payer
from utils.sanitize import sanitize_claim_data
from knowledge_base.retrieve import retrieve_context_for_claim, is_knowledge_base_available

logger = get_logger("services.appeal_pipeline")


# --- Step 0: return shape ---


@dataclass(frozen=True)
class AppealDraftResult:
    """
    Result of one successful draft run (LLM produced non-empty text).

    Attributes
    ----------
    appeal_text : str
        Generated letter body.
    filled_form_content : str or None
        Payor template filled with placeholders, if a template matched.
    filled_form_payor_name : str or None
        Folder/display name of the matched payor form.
    """

    appeal_text: str
    filled_form_content: str | None
    filled_form_payor_name: str | None


# --- Step 1: orchestrate sanitize → guidance → LLM → payor form ---


def run_appeal_draft(claim_data: dict[str, Any]) -> AppealDraftResult:
    """
    Sanitize inputs, build guidance, call the LLM, optionally fill a payor form.

    Parameters
    ----------
    claim_data :
        Raw claim fields (from the web UI JSON body or programmatic callers).

    Returns
    -------
    AppealDraftResult
        Draft text, guidance blob, and optional filled form.

    Raises
    ------
    LLMError
        If the model call fails or returns empty text.

    Notes
    -----
    Side effects: network calls to the configured LLM provider; file reads for
    CSV/forms/RAG as applicable.
    """
    with e2e_step(logger, "services.appeal_pipeline.run_appeal_draft") as pipeline_trace:
        # Step 1a — align with ``utils.sanitize`` (used before LLM).
        safe_claim = sanitize_claim_data(claim_data)
        # Step 1b — see ``build_denial_guidance_context`` below (CSV then RAG).
        guidance = build_denial_guidance_context(safe_claim)

        appeal_text = generate_appeal(safe_claim, denial_guidance_context=guidance)
        if not appeal_text or not str(appeal_text).strip():
            logger.error(
                "LLM returned empty appeal after successful call. resolution=%s",
                format_resolution_for_log(RESOLUTION_EMPTY_LLM_OUTPUT),
            )
            raise LLMError(
                "The model returned an empty appeal letter.",
                resolution_steps=RESOLUTION_EMPTY_LLM_OUTPUT,
            )

        request_type = (safe_claim.get("request_type") or "appeal").strip().lower()
        payer = safe_claim.get("payer") or ""
        filled_content, form_payor = get_filled_form_for_payer(
            payer, safe_claim, appeal_text, request_type=request_type
        )

        pipeline_trace.add(
            guidance_chars=len(guidance),
            appeal_letter_chars=len(str(appeal_text).strip()),
            payor_form_matched=bool(filled_content),
            form_payor_folder=form_payor or "",
        )
        return AppealDraftResult(
            appeal_text=str(appeal_text).strip(),
            filled_form_content=filled_content,
            filled_form_payor_name=form_payor,
        )


# --- Step 1b (detailed): CSV guidance, then optional RAG (matches ``run_appeal_draft`` call order) ---


def build_denial_guidance_context(claim_data: dict[str, Any]) -> str:
    """
    Load CSV guidance and optional Chroma RAG snippets into one string.

    Parameters
    ----------
    claim_data :
        Claim dict (uses denial_code, denial_reason, and RAG query fields).

    Returns
    -------
    str
        Text to pass as ``denial_guidance_context`` to the LLM, or empty string.

    Notes
    -----
    Any failure in CSV load, CSV match, or RAG is logged and ignored so the user
    can still get a draft from the LLM alone (intentional degraded mode). Broad
    ``except Exception`` is limited to these two blocks for that reason.
    """
    denial_code = claim_data.get("denial_code") or None
    denial_reason = claim_data.get("denial_reason") or None
    context_parts: list[str] = []

    with e2e_step(
        logger,
        "services.appeal_pipeline.build_denial_guidance_context",
        denial_code_input=denial_code or "",
    ) as guidance_trace:
        # Step 1b-i — ``utils.data_loader`` (CSV block always attempted first).
        try:
            denial_knowledge_base = load_denial_knowledge_base()
            csv_context = get_denial_knowledge_base_context(
                denial_knowledge_base,
                denial_code=denial_code,
                denial_reason=denial_reason,
            )
            if csv_context and csv_context.strip():
                context_parts.append(csv_context.strip())
                guidance_trace.add(csv_guidance_chars=len(csv_context))
        except Exception:
            logger.exception(
                "CSV denial knowledge load failed; continuing without CSV guidance. "
                "action=%s",
                format_resolution_for_log(RESOLUTION_DENIAL_CSV_LOAD_FAILED),
            )
            guidance_trace.add(csv_branch="failed_continuing")

        # Step 1b-ii — ``knowledge_base.retrieve`` (gate, then query).
        try:
            if is_knowledge_base_available():
                guidance_trace.add(chroma_marked_available=True)
                rag_context = retrieve_context_for_claim(claim_data)
                if rag_context and rag_context.strip():
                    context_parts.append(
                        "Relevant policy and guideline excerpts (use to strengthen the appeal):\n\n"
                        + rag_context.strip()
                    )
                    guidance_trace.add(rag_guidance_chars=len(rag_context))
            else:
                guidance_trace.add(chroma_marked_available=False)
        except Exception:
            logger.exception(
                "RAG retrieval failed; continuing without RAG context. action=%s",
                format_resolution_for_log(RESOLUTION_CHROMA_UNAVAILABLE + RESOLUTION_CHROMA_QUERY_FAILED),
            )
            guidance_trace.add(rag_branch="failed_continuing")

        combined = "\n\n".join(context_parts).strip()
        guidance_trace.add(
            segments_combined=len(context_parts),
            final_guidance_chars=len(combined),
        )
        return combined
