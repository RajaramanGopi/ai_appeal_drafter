"""
LLM-agnostic appeal letter generation.

Switch provider with environment variable ``LLM_PROVIDER`` (``openai`` or ``gemini``).
API keys are read from the environment only (never hardcoded).

**Read order matches ``generate_appeal()`` runtime:** public entry first, then each
provider implementation, then the handler map assigned at import (used on every call).

Timeouts
--------
Outbound calls use ``LLM_REQUEST_TIMEOUT_SECONDS`` from ``config.settings`` (overridable via env).
Calls are not retried automatically; the caller may retry at a higher layer if needed.
"""
from __future__ import annotations

import os
from typing import Any, Mapping

from dotenv import load_dotenv

from config.logging import get_logger
from config.settings import LLM_REQUEST_TIMEOUT_SECONDS
from prompt_template import build_prompt
from utils.e2e_step import e2e_step
from utils.error_support import (
    RESOLUTION_GEMINI_BLOCKED_OR_EMPTY,
    RESOLUTION_LLM_AUTH,
    RESOLUTION_LLM_NETWORK,
    RESOLUTION_LLM_NOT_CONFIGURED,
    RESOLUTION_LLM_RATE_LIMIT,
    RESOLUTION_LLM_TIMEOUT,
    RESOLUTION_OPENAI_BAD_REQUEST,
    RESOLUTION_UNEXPECTED_PIPELINE,
    format_resolution_for_log,
)

load_dotenv()
logger = get_logger("llm_client")

LLM_PROVIDER = (os.getenv("LLM_PROVIDER") or "").strip().lower()
OPENAI_MODEL = os.getenv("OPENAI_MODEL") or "gpt-4o-mini"
GEMINI_MODEL = os.getenv("GEMINI_MODEL") or "gemini-2.5-flash"


# --- Step 0: exception type ---


class LLMError(Exception):
    """
    Raised when the configured LLM provider fails (config, quota, API, or empty response).

    ``resolution_steps`` is shown in the UI and logs to guide operators (no PHI).
    """

    def __init__(self, message: str, *, resolution_steps: tuple[str, ...] | None = None) -> None:
        super().__init__(message)
        self.resolution_steps: tuple[str, ...] = tuple(resolution_steps) if resolution_steps else ()


# --- Step 0b: provider-specific error mapping ---


def _map_openai_exception(exc: BaseException) -> LLMError:
    """Convert OpenAI SDK errors into ``LLMError`` with resolution steps."""
    name = type(exc).__name__
    msg = str(exc).strip() or name
    module = type(exc).__module__

    if module.startswith("openai") or "openai" in module:
        if "AuthenticationError" in name or "401" in msg:
            return LLMError(
                "OpenAI authentication failed (invalid or missing API key).",
                resolution_steps=RESOLUTION_LLM_AUTH,
            )
        if "RateLimitError" in name or "429" in msg:
            return LLMError(
                "OpenAI rate limit or quota exceeded.",
                resolution_steps=RESOLUTION_LLM_RATE_LIMIT,
            )
        if "APITimeoutError" in name or "Timeout" in name:
            return LLMError(
                "OpenAI request timed out.",
                resolution_steps=RESOLUTION_LLM_TIMEOUT,
            )
        if "APIConnectionError" in name or "ConnectError" in name or "Connection" in name:
            return LLMError(
                "Could not reach OpenAI (connection error).",
                resolution_steps=RESOLUTION_LLM_NETWORK,
            )
        if "BadRequestError" in name or "400" in msg:
            return LLMError(
                f"OpenAI rejected the request: {msg[:400]}",
                resolution_steps=RESOLUTION_OPENAI_BAD_REQUEST,
            )
        if "NotFoundError" in name or "404" in msg:
            return LLMError(
                f"OpenAI model or resource not found: {msg[:400]}",
                resolution_steps=RESOLUTION_OPENAI_BAD_REQUEST,
            )

    return LLMError(
        f"OpenAI call failed ({name}): {msg[:500]}",
        resolution_steps=RESOLUTION_LLM_NETWORK + RESOLUTION_OPENAI_BAD_REQUEST,
    )


def _map_google_exception(exc: BaseException) -> LLMError:
    """Convert Google Gemini / API Core errors into ``LLMError`` with resolution steps."""
    name = type(exc).__name__
    msg = str(exc).strip() or name

    if "ResourceExhausted" in name or "429" in msg or "quota" in msg.lower():
        return LLMError(
            "Gemini quota or rate limit exceeded.",
            resolution_steps=RESOLUTION_LLM_RATE_LIMIT,
        )
    if "InvalidArgument" in name or "400" in msg:
        return LLMError(
            f"Gemini request was rejected: {msg[:400]}",
            resolution_steps=RESOLUTION_GEMINI_BLOCKED_OR_EMPTY,
        )
    if "DeadlineExceeded" in name or "timeout" in msg.lower() or "504" in msg:
        return LLMError(
            "Gemini request timed out.",
            resolution_steps=RESOLUTION_LLM_TIMEOUT,
        )
    if "Unauthenticated" in name or "401" in msg or "403" in msg or "API key" in msg:
        return LLMError(
            "Gemini authentication failed (check API key).",
            resolution_steps=RESOLUTION_LLM_AUTH,
        )

    return LLMError(
        f"Gemini request failed ({name}): {msg[:500]}",
        resolution_steps=RESOLUTION_GEMINI_BLOCKED_OR_EMPTY + RESOLUTION_LLM_NETWORK,
    )


def _extract_gemini_response_text(response: Any) -> tuple[str, str | None]:
    """
    Return ``(text, failure_tag)``. ``failure_tag`` is set when no usable text (for logs only).

    Avoids raising when the SDK blocks content or ``response.text`` is unavailable.
    """
    try:
        quick = response.text
        if quick is not None and str(quick).strip():
            return str(quick).strip(), None
    except (ValueError, AttributeError):
        pass

    candidates = getattr(response, "candidates", None) or []
    if not candidates:
        prompt_feedback = getattr(response, "prompt_feedback", None)
        return "", f"no_candidates_prompt_feedback={prompt_feedback!r}"

    parts_out: list[str] = []
    for cand in candidates:
        content = getattr(cand, "content", None)
        parts = getattr(content, "parts", None) if content is not None else None
        if not parts:
            continue
        for part in parts:
            text = getattr(part, "text", None)
            if text:
                parts_out.append(str(text))
    merged = "".join(parts_out).strip()
    if merged:
        return merged, None

    finish = getattr(candidates[0], "finish_reason", None)
    return "", f"no_text_finish_reason={finish!r}"


# --- Step 1: public entry — resolve provider and dispatch ---


def generate_appeal(claim_data: Mapping[str, Any], denial_guidance_context: str = "") -> str:
    """
    Generate an appeal letter using the LLM selected by configuration.

    Parameters
    ----------
    claim_data :
        Claim fields for the prompt (payer, codes, denial text, etc.). Should be
        sanitized before call when data comes from untrusted UI.
    denial_guidance_context :
        Optional CSV/RAG guidance appended in the prompt builder.

    Returns
    -------
    str
        Model-generated appeal text.

    Raises
    ------
    LLMError
        Missing keys, unknown provider, API failure, or empty model output.

    Notes
    -----
    Auth: ``OPENAI_API_KEY`` and/or ``GEMINI_API_KEY`` (or ``GOOGLE_API_KEY``).
    Timeout: ``LLM_REQUEST_TIMEOUT_SECONDS`` in environment (see ``config.settings``).
    """
    with e2e_step(
        logger,
        "llm_client.generate_appeal",
        guidance_context_chars=len(denial_guidance_context or ""),
    ) as step_trace:
        selected_llm_provider = LLM_PROVIDER
        if not selected_llm_provider:
            if os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"):
                selected_llm_provider = "gemini"
            elif os.getenv("OPENAI_API_KEY"):
                selected_llm_provider = "openai"
            else:
                logger.error(
                    "No LLM provider configured. resolution=%s",
                    format_resolution_for_log(RESOLUTION_LLM_NOT_CONFIGURED),
                )
                raise LLMError(
                    "No LLM provider is configured.",
                    resolution_steps=RESOLUTION_LLM_NOT_CONFIGURED,
                )
        step_trace.add(selected_provider=selected_llm_provider)
        if selected_llm_provider not in _LLM_PROVIDER_HANDLERS:
            logger.error("Unknown LLM_PROVIDER=%r", selected_llm_provider)
            raise LLMError(
                f"Unknown LLM_PROVIDER '{selected_llm_provider}'. Use one of: {', '.join(_LLM_PROVIDER_HANDLERS)}.",
                resolution_steps=(
                    "Set `LLM_PROVIDER=openai` or `LLM_PROVIDER=gemini` in `.env`.",
                    "See `llm_client.py` registry `_LLM_PROVIDER_HANDLERS` to add providers.",
                ),
            )
        try:
            result = _LLM_PROVIDER_HANDLERS[selected_llm_provider](
                claim_data, denial_guidance_context=denial_guidance_context
            )
            step_trace.add(response_chars=len(result), outcome="ok")
            return result
        except LLMError:
            raise
        except Exception as error:
            logger.exception(
                "Unexpected error in generate_appeal provider=%s. resolution=%s",
                selected_llm_provider,
                format_resolution_for_log(RESOLUTION_UNEXPECTED_PIPELINE),
            )
            raise LLMError(
                f"Unexpected error during appeal generation ({type(error).__name__}).",
                resolution_steps=RESOLUTION_UNEXPECTED_PIPELINE,
            ) from error


# --- Step 2: OpenAI implementation (dispatched from Step 1) ---


def _generate_openai(
    claim_data: Mapping[str, Any],
    denial_guidance_context: str = "",
) -> str:
    """Call OpenAI Chat Completions. Uses env ``OPENAI_API_KEY``. Not idempotent (creates new completion each call)."""
    logger.debug("OpenAI: start completion")
    from openai import OpenAI

    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        logger.error(
            "OPENAI_API_KEY missing. resolution=%s",
            format_resolution_for_log(RESOLUTION_LLM_AUTH),
        )
        raise LLMError(
            "OPENAI_API_KEY is not set in `.env`.",
            resolution_steps=RESOLUTION_LLM_AUTH,
        )

    openai_client = OpenAI(api_key=openai_api_key, timeout=LLM_REQUEST_TIMEOUT_SECONDS)
    with e2e_step(logger, "llm_client._generate_openai", model=OPENAI_MODEL, provider="openai") as openai_step_trace:
        prompt = build_prompt(claim_data, denial_guidance_context=denial_guidance_context)
        openai_step_trace.add(prompt_chars=len(prompt))
        try:
            with e2e_step(logger, "llm_client._generate_openai.openai_http_chat_completions"):
                response = openai_client.chat.completions.create(
                    model=OPENAI_MODEL,
                    messages=[
                        {"role": "system", "content": "You are an expert US healthcare RCM appeal specialist."},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.2,
                )
        except Exception as exc:
            logger.exception("OpenAI chat.completions failed model=%s", OPENAI_MODEL)
            raise _map_openai_exception(exc) from exc
        content = response.choices[0].message.content
        if not content or not str(content).strip():
            logger.error(
                "OpenAI returned empty content. model=%s resolution=%s",
                OPENAI_MODEL,
                format_resolution_for_log(RESOLUTION_OPENAI_BAD_REQUEST),
            )
            raise LLMError(
                "OpenAI returned no text. Check model name and API response.",
                resolution_steps=RESOLUTION_OPENAI_BAD_REQUEST,
            )
        openai_step_trace.add(response_chars=len(content))
        return content


# --- Step 3: Gemini implementation (dispatched from Step 1) ---


def _generate_gemini(
    claim_data: Mapping[str, Any],
    denial_guidance_context: str = "",
) -> str:
    """Call Google Gemini generate_content. Uses env ``GEMINI_API_KEY`` or ``GOOGLE_API_KEY``."""
    logger.debug("Gemini: start generate_content")
    import google.generativeai as genai

    gemini_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not gemini_api_key:
        logger.error(
            "Gemini API key missing. resolution=%s",
            format_resolution_for_log(RESOLUTION_LLM_AUTH),
        )
        raise LLMError(
            "GEMINI_API_KEY (or GOOGLE_API_KEY) is not set in `.env`.",
            resolution_steps=RESOLUTION_LLM_AUTH,
        )

    genai.configure(api_key=gemini_api_key)
    gemini_model = genai.GenerativeModel(
        GEMINI_MODEL,
        system_instruction="You are an expert US healthcare RCM appeal specialist.",
    )
    with e2e_step(logger, "llm_client._generate_gemini", model=GEMINI_MODEL, provider="gemini") as gemini_step_trace:
        prompt = build_prompt(claim_data, denial_guidance_context=denial_guidance_context)
        gemini_step_trace.add(prompt_chars=len(prompt))
        try:
            with e2e_step(logger, "llm_client._generate_gemini.gemini_http_generate_content"):
                response = gemini_model.generate_content(
                    prompt,
                    generation_config={"temperature": 0.2},
                    request_options={"timeout": int(LLM_REQUEST_TIMEOUT_SECONDS)},
                )
        except Exception as exc:
            logger.exception("Gemini generate_content failed model=%s", GEMINI_MODEL)
            raise _map_google_exception(exc) from exc

        text, failure_tag = _extract_gemini_response_text(response)
        if not text:
            logger.error(
                "Gemini returned no usable text model=%s detail=%s resolution=%s",
                GEMINI_MODEL,
                failure_tag,
                format_resolution_for_log(RESOLUTION_GEMINI_BLOCKED_OR_EMPTY),
            )
            raise LLMError(
                "Gemini returned no usable text (empty response, blocked content, or unsupported response shape).",
                resolution_steps=RESOLUTION_GEMINI_BLOCKED_OR_EMPTY,
            )
        gemini_step_trace.add(response_chars=len(text))
        return text


# --- Step 4: provider registry (populated at import; read after Step 2–3) ---

_LLM_PROVIDER_HANDLERS = {
    "openai": _generate_openai,
    "gemini": _generate_gemini,
}
