"""Tests for claim sanitization and log-safe summaries."""
from __future__ import annotations

from utils.sanitize import claim_data_for_log, sanitize_claim_data


def test_sanitize_claim_data_truncates_long_denial_reason(monkeypatch):
    monkeypatch.setattr("utils.sanitize.MAX_DENIAL_REASON_CHARS", 10)
    raw = {"denial_reason": "x" * 50, "cpt_code": "99213"}
    out = sanitize_claim_data(raw)
    assert out["cpt_code"] == "99213"
    assert out["denial_reason"].endswith("...")
    assert len(out["denial_reason"]) <= 10


def test_claim_data_for_log_redacts_sensitive_keys():
    data = {
        "patient_name": "Jane Doe",
        "denial_reason": "Not medically necessary",
        "cpt_code": "99213",
    }
    summary = claim_data_for_log(data)
    assert summary["patient_name"] == "[redacted]"
    assert summary["denial_reason"] == "[redacted]"
    assert summary["cpt_code"] == "99213"
