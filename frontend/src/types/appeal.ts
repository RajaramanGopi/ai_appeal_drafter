/** Aligns with FastAPI ``api/schemas.py`` JSON payloads. */

export type RequestType = 'appeal' | 'reconsideration';

export interface AppealDraftRequest {
  payer: string;
  request_type: RequestType;
  denial_code: string;
  cpt_code: string;
  icd_code: string;
  denial_reason: string;
  patient_name: string;
  dos: string;
  provider: string;
}

export interface AppealDraftResponse {
  appeal_text: string;
  filled_form_content: string | null;
  filled_form_payor_name: string | null;
  correlation_id: string;
}

export interface AppealDraftErrorBody {
  detail: string;
  resolution_steps: string[];
  correlation_id: string;
  error_type: string;
}

export interface PayorsListResponse {
  payors: string[];
}

export const initialAppealForm = (): AppealDraftRequest => ({
  payer: '',
  request_type: 'appeal',
  denial_code: '',
  cpt_code: '',
  icd_code: '',
  denial_reason: '',
  patient_name: '',
  dos: '',
  provider: '',
});
