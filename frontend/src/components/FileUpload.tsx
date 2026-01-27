import { useRef, useState } from "react";

interface FileUploadProps {
  onUpload: (file: File) => Promise<{ chunks_processed: number } | null>;
  loading: boolean;
}

export function FileUpload({ onUpload, loading }: FileUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const [success, setSuccess] = useState<number | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setFileName(file.name);
      setSuccess(null);
    }
  };

  const handleUpload = async () => {
    const file = inputRef.current?.files?.[0];
    if (!file) return;

    const result = await onUpload(file);
    if (result) {
      setSuccess(result.chunks_processed);
      setFileName(null);
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  return (
    <div className="flex items-center gap-3">
      <label className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg cursor-pointer transition-colors">
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
        </svg>
        <span className="text-sm">{fileName || "Seleccionar PDF"}</span>
        <input
          ref={inputRef}
          type="file"
          accept=".pdf"
          onChange={handleFileChange}
          className="hidden"
        />
      </label>

      {fileName && (
        <button
          onClick={handleUpload}
          disabled={loading}
          className="px-4 py-2 bg-primary hover:bg-primary-hover disabled:bg-slate-600 rounded-lg text-sm font-medium transition-colors"
        >
          {loading ? "Procesando..." : "Subir"}
        </button>
      )}

      {success !== null && (
        <span className="text-sm text-green-400 flex items-center gap-1">
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
          </svg>
          {success} chunks indexados
        </span>
      )}
    </div>
  );
}
