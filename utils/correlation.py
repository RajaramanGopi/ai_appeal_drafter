"""
Correlation ID helpers for HTTP requests.

Middleware assigns ``request.state.correlation_id`` using ``parse_correlation_header``;
routes and handlers read it with ``get_correlation_id``.
"""
from __future__ import annotations

import uuid

from starlette.requests import Request

_CORR_MAX_LEN = 128


def parse_correlation_header(value: str | None) -> str:
    """
    Normalize ``X-Correlation-ID`` or allocate a new UUID.

    Empty or whitespace-only values are replaced with a new UUID so logs always
    have a non-empty id.

    Parameters
    ----------
    value :
        Raw header value, or None if the header was absent.

    Returns
    -------
    str
        Trimmed id truncated to ``_CORR_MAX_LEN``, or a new UUID.
    """
    if value is None:
        return str(uuid.uuid4())
    stripped = value.strip()
    if not stripped:
        return str(uuid.uuid4())
    return stripped[:_CORR_MAX_LEN]


def get_correlation_id(request: Request) -> str:
    """
    Return the correlation ID for this request.

    Prefer the value set by middleware; if missing, generate a new UUID.

    Parameters
    ----------
    request :
        Current ASGI request.

    Returns
    -------
    str
        Non-empty correlation string, truncated to ``_CORR_MAX_LEN``.
    """
    raw = getattr(request.state, "correlation_id", None)
    if isinstance(raw, str) and raw.strip():
        return raw.strip()[:_CORR_MAX_LEN]
    return str(uuid.uuid4())
