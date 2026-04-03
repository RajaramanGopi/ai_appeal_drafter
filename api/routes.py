"""
Appeal draft REST endpoints.

``POST /api/v1/appeal/draft`` runs ``run_appeal_draft`` synchronously in a worker
thread (FastAPI default for def routes). Timeouts are enforced inside the LLM client.
"""
from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Request

from api.schemas import AppealDraftRequest, AppealDraftResponse, PayorsListResponse
from config.logging import get_logger
from services.appeal_pipeline import run_appeal_draft
from utils.correlation import get_correlation_id
from utils.form_loader import list_available_payors
from utils.sanitize import claim_data_for_log

logger = get_logger("api.routes")

router = APIRouter(prefix="/api/v1", tags=["appeal"])


@router.get("/payors", response_model=PayorsListResponse)
def list_payors() -> PayorsListResponse:
    """Return payor names that have templates under payor_standard_appeal_forms/."""
    return PayorsListResponse(payors=sorted(list_available_payors()))


@router.post("/appeal/draft", response_model=AppealDraftResponse)
def create_appeal_draft(body: AppealDraftRequest, request: Request) -> AppealDraftResponse:
    """
    Build a draft appeal letter and optional filled payor form from claim fields.

    Parameters
    ----------
    body :
        Claim fields from the web UI or API clients.
    request :
        Carries ``correlation_id`` on ``request.state`` (middleware in ``app.py``).

    Returns
    -------
    AppealDraftResponse
        Draft text, optional filled form, and correlation id.

    Raises
    ------
    LLMError
        Handled by the global exception handler in ``app.py`` (502 to client).
    """
    correlation_id = get_correlation_id(request)
    claim_data: dict[str, Any] = body.model_dump()
    started = time.perf_counter()
    logger.info(
        "[E2E] START method=api.routes.create_appeal_draft correlation_id=%s claim_summary=%s",
        correlation_id,
        claim_data_for_log(claim_data),
    )
    try:
        result = run_appeal_draft(claim_data)
    finally:
        elapsed_ms = (time.perf_counter() - started) * 1000
        logger.info(
            "[E2E] END method=api.routes.create_appeal_draft correlation_id=%s duration_ms=%.2f",
            correlation_id,
            elapsed_ms,
        )

    logger.info(
        "[E2E] API_RESPONSE method=api.routes.create_appeal_draft correlation_id=%s appeal_chars=%s form_payor=%s",
        correlation_id,
        len(result.appeal_text),
        result.filled_form_payor_name or "",
    )
    return AppealDraftResponse(
        appeal_text=result.appeal_text,
        filled_form_content=result.filled_form_content,
        filled_form_payor_name=result.filled_form_payor_name,
        correlation_id=correlation_id,
    )


