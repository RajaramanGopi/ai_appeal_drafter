import type { AppealDraftRequest, PayorsListResponse } from '../types/appeal';

function assertOk(response: Response, context: string): void {
  if (!response.ok) {
    throw new Error(`${context}: HTTP ${response.status}`);
  }
}

/**
 * Lists payor folders that have standard appeal templates.
 */
export async function fetchPayors(): Promise<PayorsListResponse> {
  const response = await fetch('/api/v1/payors');
  assertOk(response, 'fetchPayors');
  return response.json() as Promise<PayorsListResponse>;
}

/**
 * POST draft request; returns the raw Response so callers can read status, headers, and JSON.
 */
export async function postAppealDraft(
  body: AppealDraftRequest,
  correlationId: string,
): Promise<Response> {
  return fetch('/api/v1/appeal/draft', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Correlation-ID': correlationId,
    },
    body: JSON.stringify(body),
  });
}
