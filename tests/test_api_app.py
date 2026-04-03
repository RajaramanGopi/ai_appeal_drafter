"""Smoke tests for the FastAPI app (draft endpoint mocked)."""
from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from services.appeal_pipeline import AppealDraftResult


@pytest.fixture
def client() -> TestClient:
    from app import app

    return TestClient(app)


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_payors_list_shape(client: TestClient) -> None:
    response = client.get("/api/v1/payors")
    assert response.status_code == 200
    body = response.json()
    assert "payors" in body
    assert isinstance(body["payors"], list)


def test_root_serves_html(client: TestClient) -> None:
    response = client.get("/")
    if response.status_code == 503:
        pytest.skip("React UI not built (cd frontend && npm run build)")
    assert response.status_code == 200
    ctype = response.headers.get("content-type", "").lower()
    assert "text/html" in ctype
    assert b'id="root"' in response.content or b"id='root'" in response.content


@patch("api.routes.run_appeal_draft")
def test_draft_success_returns_json(mock_run, client: TestClient) -> None:
    mock_run.return_value = AppealDraftResult(
        appeal_text="Sample letter body.",
        filled_form_content=None,
        filled_form_payor_name=None,
    )
    response = client.post(
        "/api/v1/appeal/draft",
        json={
            "payer": "TestPayer",
            "request_type": "appeal",
            "denial_code": "",
            "cpt_code": "",
            "icd_code": "",
            "denial_reason": "",
            "patient_name": "",
            "dos": "",
            "provider": "",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["appeal_text"] == "Sample letter body."
    assert data["filled_form_content"] is None
    assert "correlation_id" in data
    assert response.headers.get("X-Correlation-ID")


@patch("api.routes.run_appeal_draft")
def test_draft_llm_error_returns_502(mock_run, client: TestClient) -> None:
    from llm_client import LLMError

    mock_run.side_effect = LLMError("upstream failed", resolution_steps=("Check API key.",))
    response = client.post(
        "/api/v1/appeal/draft",
        json={
            "payer": "",
            "request_type": "appeal",
            "denial_code": "",
            "cpt_code": "",
            "icd_code": "",
            "denial_reason": "",
            "patient_name": "",
            "dos": "",
            "provider": "",
        },
    )
    assert response.status_code == 502
    data = response.json()
    assert data["error_type"] == "llm_error"
    assert "Check API key" in data["resolution_steps"][0]
