import { useCallback, useState } from "react";
import type { ChatResponse, Document, IngestResponse } from "../types";

const API_URL = "/api";

interface DocumentsResponse {
  status: string;
  documents: { name: string; chunks: number }[];
}

interface UseRFPReturn {
  loading: boolean;
  error: string | null;
  uploadDocument: (file: File) => Promise<IngestResponse | null>;
  askQuestion: (question: string) => Promise<ChatResponse | null>;
  fetchDocuments: () => Promise<Document[]>;
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

  const fetchDocuments = useCallback(async (): Promise<Document[]> => {
    try {
      const response = await fetch(`${API_URL}/documents`);
      if (!response.ok) return [];
      const data: DocumentsResponse = await response.json();
      return data.documents.map((doc) => ({
        name: doc.name,
        chunks: doc.chunks,
        uploadedAt: new Date(), // Approximate, since we don't store upload time
      }));
    } catch {
      return [];
    }
  }, []);

  const clearError = useCallback(() => setError(null), []);

  return { loading, error, uploadDocument, askQuestion, fetchDocuments, clearError };
}
