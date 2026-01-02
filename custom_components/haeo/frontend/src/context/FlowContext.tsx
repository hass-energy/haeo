/**
 * Flow context for managing config flow state.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useSearchParams } from "react-router-dom";
import {
  clearDraft,
  loadDraft,
  parseFlowParams,
  pingFlow,
  saveDraft,
  submitFlow,
} from "../api/flow";
import type { FlowParams, FlowResult } from "../types";

/** Form data type - flexible to allow any field */
export type FormData = Record<string, unknown>;

/** Keep-alive ping interval (2 minutes) */
const PING_INTERVAL = 2 * 60 * 1000;

/** Auto-save draft interval (30 seconds) */
const DRAFT_SAVE_INTERVAL = 30 * 1000;

interface FlowContextValue {
  /** Flow parameters from URL */
  params: FlowParams | null;
  /** Current form data */
  formData: FormData;
  /** Whether the flow is still active */
  isActive: boolean;
  /** Whether form submission is in progress */
  isSubmitting: boolean;
  /** Flow result after submission */
  result: FlowResult | null;
  /** Error message if any */
  error: string | null;
  /** Update form data */
  setFormData: (data: FormData) => void;
  /** Update a single field */
  updateField: (field: string, value: unknown) => void;
  /** Submit the flow */
  submit: () => Promise<void>;
  /** Clear error state */
  clearError: () => void;
}

const FlowContext = createContext<FlowContextValue | null>(null);

interface FlowProviderProps {
  children: ReactNode;
}

/**
 * Provider for config flow state management.
 */
export function FlowProvider({ children }: FlowProviderProps) {
  const [searchParams] = useSearchParams();
  const [formData, setFormDataState] = useState<FormData>({});
  const [isActive, setIsActive] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [result, setResult] = useState<FlowResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Parse flow params from URL
  const params = useMemo(() => {
    try {
      return parseFlowParams(searchParams);
    } catch (e) {
      console.error("Invalid flow params:", e);
      return null;
    }
  }, [searchParams]);

  // Load saved draft on mount
  useEffect(() => {
    if (params?.flowId) {
      const draft = loadDraft(params.flowId);
      if (draft) {
        setFormDataState(draft);
      }
    }
  }, [params?.flowId]);

  // Keep-alive ping
  useEffect(() => {
    if (!params?.flowId || !isActive) return;

    const interval = setInterval(async () => {
      const alive = await pingFlow(params.flowId);
      if (!alive) {
        setIsActive(false);
        setError("Flow expired. Your draft has been saved.");
      }
    }, PING_INTERVAL);

    return () => clearInterval(interval);
  }, [params?.flowId, isActive]);

  // Auto-save draft
  useEffect(() => {
    if (!params?.flowId || !isActive) return;

    const interval = setInterval(() => {
      if (Object.keys(formData).length > 0) {
        saveDraft(params.flowId, formData);
      }
    }, DRAFT_SAVE_INTERVAL);

    return () => clearInterval(interval);
  }, [params?.flowId, formData, isActive]);

  const setFormData = useCallback((data: FormData) => {
    setFormDataState(data);
  }, []);

  const updateField = useCallback((field: string, value: unknown) => {
    setFormDataState((prev) => ({ ...prev, [field]: value }));
  }, []);

  const submit = useCallback(async () => {
    if (!params?.flowId) {
      setError("No flow ID available");
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const flowResult = await submitFlow(
        params.flowId,
        formData
      );
      setResult(flowResult);

      // Clear draft on successful submission
      if (
        flowResult.type === "create_entry" ||
        flowResult.type === "external_step_done"
      ) {
        clearDraft(params.flowId);
      }

      // Handle errors from flow
      if (flowResult.errors && Object.keys(flowResult.errors).length > 0) {
        const errorMessages = Object.entries(flowResult.errors)
          .map(([field, msg]) => `${field}: ${msg}`)
          .join(", ");
        setError(errorMessages);
      }
    } catch (e) {
      const message = e instanceof Error ? e.message : "Submission failed";
      setError(message);
    } finally {
      setIsSubmitting(false);
    }
  }, [params?.flowId, formData]);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const value: FlowContextValue = {
    params,
    formData,
    isActive,
    isSubmitting,
    result,
    error,
    setFormData,
    updateField,
    submit,
    clearError,
  };

  return <FlowContext.Provider value={value}>{children}</FlowContext.Provider>;
}

/**
 * Hook to access flow context.
 */
export function useFlow(): FlowContextValue {
  const context = useContext(FlowContext);
  if (!context) {
    throw new Error("useFlow must be used within a FlowProvider");
  }
  return context;
}
