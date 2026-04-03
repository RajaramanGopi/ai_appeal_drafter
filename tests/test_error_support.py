"""Operational error helper strings."""
from __future__ import annotations

from utils.error_support import format_resolution_for_log


def test_format_resolution_for_log_joins_steps():
    steps = ("First step.", "Second step.")
    assert "First step." in format_resolution_for_log(steps)
    assert "Second step." in format_resolution_for_log(steps)


def test_format_resolution_empty():
    assert format_resolution_for_log(()) == ""
