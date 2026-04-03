"""
End-to-end step timing and structured log lines for workflow review.

Log format: ``[E2E] START|END method=...`` with ``duration_ms`` and key=value details.
Use ``add()`` on the context object to attach outcome metrics before the step closes.

Previews of long strings should omit raw PHI; use for reference KB/RAG text only.

**Read order matches typical construction:** string preview helper, key-value formatter
(used inside ``e2e_step``), then the context manager class.
"""
from __future__ import annotations

import time
from typing import Any


# --- Step 0: standalone preview helper (no dependency on the class below) ---


def preview_text(text: str, max_len: int = 400) -> str:
    """Single-line preview safe for log lines (newlines collapsed)."""
    if not text:
        return ""
    single_line = " ".join(text.split())
    if len(single_line) <= max_len:
        return single_line
    return single_line[: max_len - 3] + "..."


# --- Step 1: log line fragment builder (used by ``e2e_step.__enter__`` / ``__exit__``) ---


def _format_key_value_pairs(**kw: Any) -> str:
    parts: list[str] = []
    for key in sorted(kw):
        value = kw[key]
        if value is None:
            continue
        parts.append(f"{key}={value!r}")
    return " ".join(parts)


# --- Step 2: context manager implementation ---


class e2e_step:
    """
    Context manager: log step start, duration, and optional start/end metadata.

    Examples
    --------
    >>> with e2e_step(logger, "module.fn", denial_code="N362") as step:
    ...     result = work()
    ...     step.add(output_chars=len(result))
    """

    __slots__ = ("logger", "method", "start_kw", "_t0", "end_kw")

    def __init__(self, logger, method: str, **start_kw: Any) -> None:
        self.logger = logger
        self.method = method
        self.start_kw = {k: v for k, v in start_kw.items() if v is not None and v != ""}
        self._t0 = 0.0
        self.end_kw: dict[str, Any] = {}

    def add(self, **kwargs: Any) -> None:
        """Attach fields logged on END (outcome sizes, previews, flags)."""
        for key, value in kwargs.items():
            if value is not None and value != "":
                self.end_kw[key] = value

    def __enter__(self) -> e2e_step:
        self._t0 = time.perf_counter()
        start_msg = _format_key_value_pairs(**self.start_kw)
        if start_msg:
            self.logger.info("[E2E] START method=%s %s", self.method, start_msg)
        else:
            self.logger.info("[E2E] START method=%s", self.method)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        elapsed_ms = (time.perf_counter() - self._t0) * 1000
        if exc_type is not None:
            self.end_kw.setdefault("exception", exc_type.__name__)
        tail = _format_key_value_pairs(**self.end_kw)
        if tail:
            self.logger.info(
                "[E2E] END method=%s duration_ms=%.2f %s",
                self.method,
                elapsed_ms,
                tail,
            )
        else:
            self.logger.info("[E2E] END method=%s duration_ms=%.2f", self.method, elapsed_ms)
