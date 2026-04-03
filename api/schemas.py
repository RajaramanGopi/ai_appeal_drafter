"""
Pydantic models for the appeal draft HTTP API.

Request bodies mirror the claim dict passed to ``run_appeal_draft`` from the former
Streamlit UI. Responses are JSON-safe (no PHI in field names beyond business keys).
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class AppealDraftRequest(BaseModel):
    """Claim and denial fields submitted from the web UI or an API client."""

    payer: str = Field(default="", description="Payer name; match payor_standard_appeal_forms folder when possible.")
    request_type: Literal["appeal", "reconsideration"] = "appeal"
    denial_code: str = ""
    cpt_code: str = ""
    icd_code: str = ""
    denial_reason: str = ""
    patient_name: str = ""
    dos: str = Field(default="", description="Date of service (free text).")
    provider: str = ""


class AppealDraftResponse(BaseModel):
    """Successful draft payload returned to the client."""

    appeal_text: str
    filled_form_content: str | None = None
    filled_form_payor_name: str | None = None
    correlation_id: str


class AppealDraftErrorResponse(BaseModel):
    """Structured error body for LLM or pipeline failures (no PHI)."""

    detail: str
    resolution_steps: list[str] = Field(default_factory=list)
    correlation_id: str
    error_type: str = "llm_error"


class PayorsListResponse(BaseModel):
    """Payor folder names that have standard forms available."""

    payors: list[str]
