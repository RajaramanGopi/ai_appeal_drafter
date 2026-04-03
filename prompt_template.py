"""
Build the natural-language prompt sent to the LLM for appeal or reconsideration letters.

``build_prompt`` applies ``sanitize_claim_data`` again for defense in depth when
callers forget to sanitize first.

**Execution:** a single Step 1 entry — ``llm_client.generate_appeal`` → ``build_prompt``.
"""
from __future__ import annotations

from typing import Any, Mapping

from config.logging import get_logger
from utils.e2e_step import e2e_step
from utils.sanitize import sanitize_claim_data

logger = get_logger("prompt_template")


# --- Step 1: compose user message for Chat / Gemini ---


def build_prompt(claim_data: Mapping[str, Any], denial_guidance_context: str = "") -> str:
    """
    Compose the user message for the appeal or reconsideration draft.

    Parameters
    ----------
    claim_data :
        Claim fields (patient, payer, codes, denial reason, request_type, etc.).
    denial_guidance_context :
        Optional CSV/RAG block inserted before claim details when non-empty.

    Returns
    -------
    str
        Full user prompt string (not logged at INFO in full; lengths may be logged).

    Notes
    -----
    Side effects: none (pure string build). Output may contain PHI if ``claim_data`` does;
    callers must ensure compliance before sending to third-party APIs.
    """
    with e2e_step(
        logger,
        "prompt_template.build_prompt",
        guidance_context_chars=len(denial_guidance_context or ""),
    ) as step_trace:
        safe = sanitize_claim_data(dict(claim_data))
        request_type = (safe.get("request_type") or "appeal").strip().lower()
        letter_type = "reconsideration request" if request_type == "reconsideration" else "appeal letter"

        optional_guidance_section = ""
        if denial_guidance_context and denial_guidance_context.strip():
            optional_guidance_section = f"""
Use the following denial-specific guidance when drafting the {letter_type}. Follow the appeal strategy, mention the suggested medical documents to be attached, and adhere to any payer notes and guidelines below.

{denial_guidance_context}

"""

        prompt = f"""
Write a professional medical insurance {letter_type} for the payer and denial below.
Appeal/Reconsideration content should not cross more than 10 lines with deterministic request and accuracy for the denial reason.

{optional_guidance_section}Claim Details:

Patient: {safe.get('patient_name', 'N/A')}
Date of Service: {safe.get('dos', 'N/A')}
Provider: {safe.get('provider', 'N/A')}

Payer: {safe.get('payer', 'N/A')}
Denial Code: {safe.get('denial_code', 'N/A')}
CPT: {safe.get('cpt_code', 'N/A')}
ICD: {safe.get('icd_code', 'N/A')}

Denial Reason:
{safe.get('denial_reason', 'Not specified')}

Reliability: Do not invent payer-specific mailing addresses, fax numbers, portal URLs, or statutory deadlines. When such details would normally appear in a letter, use clear placeholders (e.g., "per the address on the remittance advice") unless they are explicitly provided in the claim details or guidance above. Ground medical and coding arguments in the denial codes and reasons given.

Write a formal {letter_type} that includes:

1. Clinical justification
2. Medical necessity (where applicable)
3. Clear request for {request_type.replace('_', ' ')}

When denial guidance was provided above, align your wording with the suggested appeal strategy and reference the types of documentation that should be attached. End with a placeholder for provider signature.
""".strip()

        step_trace.add(
            letter_type=letter_type,
            request_type=request_type,
            prompt_total_chars=len(prompt),
            guidance_block_used=bool(denial_guidance_context and denial_guidance_context.strip()),
            denial_code_for_prompt=safe.get("denial_code") or "",
            cpt_for_prompt=safe.get("cpt_code") or "",
            icd_for_prompt=safe.get("icd_code") or "",
        )
        return prompt
