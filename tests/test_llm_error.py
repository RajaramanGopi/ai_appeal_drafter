"""LLMError carries optional resolution steps for operators."""
from __future__ import annotations

from llm_client import LLMError


def test_llm_error_default_steps_empty():
    err = LLMError("test")
    assert str(err) == "test"
    assert err.resolution_steps == ()


def test_llm_error_with_resolution_steps():
    steps = ("Do A.", "Do B.")
    err = LLMError("failed", resolution_steps=steps)
    assert err.resolution_steps == steps
