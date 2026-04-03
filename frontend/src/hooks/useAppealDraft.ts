import { useCallback, useEffect, useState } from 'react';

import { fetchPayors, postAppealDraft } from '../api/appealApi';
import { formatErrorDetail } from '../api/errorFormatting';
import type {
  AppealDraftErrorBody,
  AppealDraftRequest,
  AppealDraftResponse,
} from '../types/appeal';
import { initialAppealForm } from '../types/appeal';

function newCorrelationId(): string {
  return globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export interface UseAppealDraftState {
  form: AppealDraftRequest;
  setFormField: <K extends keyof AppealDraftRequest>(key: K, value: AppealDraftRequest[K]) => void;
  loading: boolean;
  payorsCaption: string;
  result: AppealDraftResponse | null;
  apiError: AppealDraftErrorBody | null;
  networkError: string | null;
  noFormInfo: string;
  filledFormText: string;
  setFilledFormText: (value: string) => void;
  formDownloadSlug: string;
  submit: () => Promise<void>;
}

export function useAppealDraft(): UseAppealDraftState {
  const [form, setForm] = useState<AppealDraftRequest>(initialAppealForm);
  const [loading, setLoading] = useState(false);
  const [payorsCaption, setPayorsCaption] = useState('');
  const [result, setResult] = useState<AppealDraftResponse | null>(null);
  const [apiError, setApiError] = useState<AppealDraftErrorBody | null>(null);
  const [networkError, setNetworkError] = useState<string | null>(null);
  const [noFormInfo, setNoFormInfo] = useState('');
  const [filledFormText, setFilledFormText] = useState('');
  const [formDownloadSlug, setFormDownloadSlug] = useState('form');

  useEffect(() => {
    let cancelled = false;
    fetchPayors()
      .then((res) => {
        if (cancelled || !res.payors?.length) return;
        setPayorsCaption(`Standard forms available for: ${res.payors.join(', ')}`);
      })
      .catch(() => {
        if (!cancelled) setPayorsCaption('');
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const setFormField = useCallback(<K extends keyof AppealDraftRequest>(key: K, value: AppealDraftRequest[K]) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  }, []);

  const submit = useCallback(async () => {
    setLoading(true);
    setResult(null);
    setApiError(null);
    setNetworkError(null);
    setNoFormInfo('');
    setFilledFormText('');

    const correlationId = newCorrelationId();
    const payload: AppealDraftRequest = {
      payer: form.payer.trim(),
      request_type: form.request_type,
      denial_code: form.denial_code.trim(),
      cpt_code: form.cpt_code.trim(),
      icd_code: form.icd_code.trim(),
      denial_reason: form.denial_reason.trim(),
      patient_name: form.patient_name.trim(),
      dos: form.dos.trim(),
      provider: form.provider.trim(),
    };

    try {
      const response = await postAppealDraft(payload, correlationId);
      const echoedId = response.headers.get('X-Correlation-ID') ?? correlationId;

      if (!response.ok) {
        let raw: Record<string, unknown>;
        try {
          raw = (await response.json()) as Record<string, unknown>;
        } catch {
          setNetworkError(`Request failed (${response.status})`);
          return;
        }
        const detail = formatErrorDetail(raw.detail);
        const steps = Array.isArray(raw.resolution_steps)
          ? (raw.resolution_steps as string[])
          : [];
        const cid = typeof raw.correlation_id === 'string' ? raw.correlation_id : echoedId;
        const errorType = typeof raw.error_type === 'string' ? raw.error_type : 'error';
        setApiError({
          detail,
          resolution_steps: steps,
          correlation_id: cid,
          error_type: errorType,
        });
        return;
      }

      const data = (await response.json()) as AppealDraftResponse;
      const merged: AppealDraftResponse = {
        ...data,
        correlation_id: data.correlation_id || echoedId,
      };
      setResult(merged);

      if (merged.filled_form_content) {
        setFilledFormText(merged.filled_form_content);
        setFormDownloadSlug((merged.filled_form_payor_name ?? 'form').replace(/\s+/g, '_'));
      } else if (payload.payer && payorsCaption) {
        setNoFormInfo(`No standard form matched "${payload.payer}". ${payorsCaption}`);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setNetworkError(message);
    } finally {
      setLoading(false);
    }
  }, [form, payorsCaption]);

  return {
    form,
    setFormField,
    loading,
    payorsCaption,
    result,
    apiError,
    networkError,
    noFormInfo,
    filledFormText,
    setFilledFormText,
    formDownloadSlug,
    submit,
  };
}
