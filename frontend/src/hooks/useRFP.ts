import { useCallback, useState } from "react";

const API_URL = "http://localhost:8000/api";

interface IngestResponse {
  status: string;
  filename: string;
  chunks_processed: number;
}

interface ChatResponse {
  answer: string;
  sources: string[];
}

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

  const uploadDocument = useCallback(async (file: File): Promise<IngestResponse | null> => {
    setLoading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(`${API_URL}/ingest`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || "Error al subir documento");
      }

      return await response.json();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error desconocido");
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const askQuestion = useCallback(async (question: string): Promise<ChatResponse | null> => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || "Error al procesar pregunta");
      }

      return await response.json();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error desconocido");
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const clearError = useCallback(() => setError(null), []);

  return { loading, error, uploadDocument, askQuestion, clearError };
}
