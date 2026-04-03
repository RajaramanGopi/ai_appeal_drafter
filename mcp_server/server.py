"""
FastMCP server: tools and prompts for appeal drafting (stdio by default).

Logging goes to **stderr** and ``logs/appeal_drafter.log`` only so stdout stays clean for MCP JSON-RPC.

**Read order:** bootstrap env/logging → FastMCP app → tools/resources/prompts → ``run_mcp_server``.
"""
from __future__ import annotations

import json
import sys
from typing import Any

from dotenv import load_dotenv

load_dotenv()

from config.logging import configure_logging, get_logger

configure_logging(log_to_file=True, log_console_stream=sys.stderr)

from mcp.server.fastmcp import FastMCP

from knowledge_base.retrieve import is_knowledge_base_available, retrieve_context_for_claim
from llm_client import LLMError
from services.appeal_pipeline import build_denial_guidance_context, run_appeal_draft
from utils.form_loader import list_available_payors

logger = get_logger("mcp_server.server")

mcp = FastMCP(
    "Appeal Drafter AI",
    instructions=(
        "Tools for drafting US healthcare claim appeals and reconsiderations using the "
        "Appeal Drafter pipeline (CSV denial guidance, optional Chroma RAG, LLM draft, payor forms). "
        "Do not log or retain PHI beyond what the user supplies in tool arguments."
    ),
)


def _claim_payload(
    payer: str = "",
    patient_name: str = "",
    dos: str = "",
    provider: str = "",
    denial_code: str = "",
    cpt_code: str = "",
    icd_code: str = "",
    denial_reason: str = "",
    request_type: str = "appeal",
) -> dict[str, Any]:
    """Build the claim dict used by the pipeline (same shape as Streamlit)."""
    rt = (request_type or "appeal").strip().lower()
    if rt not in ("appeal", "reconsideration"):
        rt = "appeal"
    return {
        "payer": payer.strip(),
        "patient_name": patient_name.strip(),
        "dos": dos.strip(),
        "provider": provider.strip(),
        "denial_code": denial_code.strip(),
        "cpt_code": cpt_code.strip(),
        "icd_code": icd_code.strip(),
        "denial_reason": denial_reason.strip(),
        "request_type": rt,
    }


@mcp.tool()
def draft_appeal_letter(
    payer: str = "",
    patient_name: str = "",
    dos: str = "",
    provider: str = "",
    denial_code: str = "",
    cpt_code: str = "",
    icd_code: str = "",
    denial_reason: str = "",
    request_type: str = "appeal",
) -> dict[str, Any]:
    """
    Generate a full appeal or reconsideration draft via the configured LLM (OpenAI or Gemini).
    Uses denial CSV guidance, optional RAG, and fills a payor template when the payer name matches
    a folder under payor_standard_appeal_forms/. Requires API keys in .env.
    """
    claim = _claim_payload(
        payer=payer,
        patient_name=patient_name,
        dos=dos,
        provider=provider,
        denial_code=denial_code,
        cpt_code=cpt_code,
        icd_code=icd_code,
        denial_reason=denial_reason,
        request_type=request_type,
    )
    logger.info(
        "MCP tool draft_appeal_letter payer_nonempty=%s denial_code_nonempty=%s",
        bool(claim.get("payer")),
        bool(claim.get("denial_code")),
    )
    try:
        result = run_appeal_draft(claim)
    except LLMError as err:
        logger.warning("MCP draft_appeal_letter LLMError: %s", err)
        return {
            "success": False,
            "error": str(err),
            "resolution_steps": list(err.resolution_steps),
            "appeal_text": "",
            "filled_form_content": None,
            "filled_form_payor_name": None,
        }
    except Exception as err:
        logger.exception("MCP draft_appeal_letter unexpected error")
        return {
            "success": False,
            "error": f"{type(err).__name__}: {err}",
            "resolution_steps": [],
            "appeal_text": "",
            "filled_form_content": None,
            "filled_form_payor_name": None,
        }
    return {
        "success": True,
        "error": None,
        "resolution_steps": [],
        "appeal_text": result.appeal_text,
        "filled_form_content": result.filled_form_content,
        "filled_form_payor_name": result.filled_form_payor_name,
    }


@mcp.tool()
def get_denial_and_policy_guidance(
    payer: str = "",
    denial_code: str = "",
    denial_reason: str = "",
    cpt_code: str = "",
    icd_code: str = "",
) -> dict[str, Any]:
    """
    Return CSV-based denial guidance plus optional Chroma RAG excerpts (no LLM call).
    Use to inspect what context would be injected before drafting.
    """
    claim = _claim_payload(
        payer=payer,
        denial_code=denial_code,
        denial_reason=denial_reason,
        cpt_code=cpt_code,
        icd_code=icd_code,
    )
    guidance = build_denial_guidance_context(claim)
    rag = ""
    rag_error = None
    try:
        if is_knowledge_base_available():
            rag = retrieve_context_for_claim(claim)
    except Exception as err:
        rag_error = f"{type(err).__name__}: {err}"
        logger.warning("MCP get_denial_and_policy_guidance RAG failed: %s", rag_error)
    return {
        "combined_guidance_chars": len(guidance) + len(rag),
        "csv_and_rag_text": (guidance + ("\n\n" + rag if rag else "")).strip() or None,
        "rag_retrieved": bool(rag and rag.strip()),
        "rag_error": rag_error,
    }


@mcp.tool()
def list_payor_form_templates() -> dict[str, Any]:
    """List payor folder names that have appeal_form.txt / reconsideration_form.txt templates."""
    names = list_available_payors()
    return {"payors": names, "count": len(names)}


@mcp.tool()
def rag_index_status() -> dict[str, Any]:
    """Whether the local Chroma RAG index is available (chroma_db + collection)."""
    return {
        "knowledge_base_available": is_knowledge_base_available(),
        "hint": "Run: python -m knowledge_base.ingest [--urls] from project root if false.",
    }


@mcp.resource("appeal-drafter://payor-form-templates")
def resource_payor_templates() -> str:
    """JSON list of payor names with standard form templates."""
    return json.dumps({"payors": list_available_payors()}, indent=2)


@mcp.prompt()
def appeal_letter_workflow(
    payer: str = "",
    denial_summary: str = "",
) -> str:
    """Suggested steps for the assistant when helping a user draft an appeal."""
    return f"""You are assisting with a US healthcare claim appeal.

Payer (if known): {payer or "(not provided)"}
Denial summary: {denial_summary or "(ask the user for denial code, CPT/ICD, and EOB reason)"}

Workflow:
1. Call rag_index_status if policy context might help.
2. Call get_denial_and_policy_guidance with structured fields when the user provides codes.
3. Call draft_appeal_letter with the same fields to produce the letter (and payor form if matched).
4. Remind the user to verify deadlines and submission addresses on the EOB or portal; do not invent them.
"""


def run_mcp_server() -> None:
    """Start the MCP server on stdio (for Cursor, Claude Desktop, MCP Inspector)."""
    logger.info("MCP server starting (stdio transport); logs on stderr and logs/appeal_drafter.log")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    run_mcp_server()
