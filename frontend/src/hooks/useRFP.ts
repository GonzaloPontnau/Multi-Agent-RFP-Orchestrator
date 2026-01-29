import { useCallback, useState } from "react";
import type { ChatResponse, IngestResponse } from "../types";

const API_URL = "/api";

interface UseRFPReturn {
  loading: boolean;
  error: string | null;
  uploadDocument: (file: File) => Promise<IngestResponse | null>;
  askQuestion: (question: string) => Promise<ChatResponse | null>;
  clearError: () => void;
}

export function useRFP(): UseRFPReturn {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const apiCall = useCallback(async <T>(
    endpoint: string,
    options: RequestInit,
    errorMsg: string
  ): Promise<T | null> => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_URL}${endpoint}`, options);
      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || errorMsg);
      }
      return await response.json();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error desconocido");
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const uploadDocument = useCallback(async (file: File): Promise<IngestResponse | null> => {
    const formData = new FormData();
    formData.append("file", file);
    return apiCall<IngestResponse>("/ingest", { method: "POST", body: formData }, "Error al subir documento");
  }, [apiCall]);

  const askQuestion = useCallback(async (question: string): Promise<ChatResponse | null> => {
    return apiCall<ChatResponse>("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    }, "Error al procesar pregunta");
  }, [apiCall]);

  const clearError = useCallback(() => setError(null), []);

  return { loading, error, uploadDocument, askQuestion, clearError };
}

