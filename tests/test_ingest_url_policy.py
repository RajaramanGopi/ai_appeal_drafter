"""SSRF-related URL policy helpers (no live HTTP)."""
from __future__ import annotations

import unittest.mock as mock

from knowledge_base import ingest


def test_https_only():
    assert ingest._is_safe_public_https_url("http://example.com/doc") is False


def test_host_allowlist_blocks_unknown_host(monkeypatch):
    monkeypatch.setattr(ingest, "INGEST_URL_HOST_ALLOWLIST", frozenset({"allowed.example"}))
    with mock.patch("knowledge_base.ingest.socket.getaddrinfo") as ga:
        # Use a routable global address; TEST-NET IPs are not is_global in ipaddress.
        ga.return_value = [(None, None, None, None, ("8.8.8.8", 443))]
        assert ingest._is_safe_public_https_url("https://allowed.example/p") is True
        assert ingest._is_safe_public_https_url("https://other.example/p") is False


def test_non_global_ip_rejected(monkeypatch):
    monkeypatch.setattr(ingest, "INGEST_URL_HOST_ALLOWLIST", frozenset({"allowed.example"}))
    with mock.patch("knowledge_base.ingest.socket.getaddrinfo") as ga:
        ga.return_value = [(None, None, None, None, ("10.0.0.2", 443))]
        assert ingest._is_safe_public_https_url("https://allowed.example/p") is False


def test_host_matches_allowlist_subdomain(monkeypatch):
    monkeypatch.setattr(ingest, "INGEST_URL_HOST_ALLOWLIST", frozenset({"cms.gov"}))
    assert ingest._host_matches_allowlist("api.cms.gov") is True
    assert ingest._host_matches_allowlist("CMS.GOV.") is True
