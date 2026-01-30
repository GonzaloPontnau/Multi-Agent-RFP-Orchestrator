import { useState } from "react";
import type { Document } from "../types";

interface SidebarProps {
  documents: Document[];
  onUpload: (file: File) => Promise<{ chunks_processed: number } | null>;
  loading: boolean;
}

export function Sidebar({ documents, onUpload, loading }: SidebarProps) {
  const [dragOver, setDragOver] = useState(false);

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file?.name.endsWith(".pdf")) {
      await onUpload(file);
    }
  };

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      await onUpload(file);
      e.target.value = "";
    }
  };

  return (
    <aside className="w-72 bg-gradient-to-b from-slate-900 to-slate-900/95 border-r border-slate-800/50 flex flex-col">
      {/* Logo */}
      <div className="p-6">
        <div className="flex items-center gap-4">
          <div className="relative">
            <div className="absolute inset-0 bg-orange-500/20 rounded-full blur-lg" />
            <img 
              src="/logo.png" 
              alt="TenderCortex" 
              className="relative w-11 h-11 rounded-full object-cover ring-2 ring-orange-500/30"
            />
          </div>
          <div>
            <h1 className="font-semibold text-white">TenderCortex</h1>
            <p className="text-xs text-slate-500">Multi-Agent Intelligence</p>
          </div>
        </div>
      </div>

      {/* Divider */}
      <div className="mx-5 h-px bg-gradient-to-r from-transparent via-slate-700/50 to-transparent" />

      {/* Upload Area */}
      <div className="p-5">
        <label
          className={`block border-2 border-dashed rounded-3xl p-7 text-center cursor-pointer transition-all duration-300 ${
            dragOver
              ? "border-orange-500/70 bg-orange-500/10 scale-[1.02]"
              : "border-slate-700/50 hover:border-slate-600/70 hover:bg-slate-800/30"
          }`}
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
        >
          <input
            type="file"
            accept=".pdf"
            onChange={handleFileSelect}
            className="hidden"
            disabled={loading}
          />
          {loading ? (
            <div className="flex flex-col items-center gap-3">
              <div className="w-10 h-10 border-2 border-orange-500/50 border-t-orange-500 rounded-full animate-spin" />
              <span className="text-sm text-slate-400">Procesando...</span>
            </div>
          ) : (
            <>
              <div className="w-14 h-14 mx-auto mb-3 rounded-2xl bg-slate-800/50 flex items-center justify-center">
                <svg className="w-7 h-7 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
              </div>
              <p className="text-sm text-slate-400">Arrastra un PDF aqui</p>
              <p className="text-xs text-slate-600 mt-1">o haz click para seleccionar</p>
            </>
          )}
        </label>
      </div>

      {/* Documents List */}
      <div className="flex-1 overflow-y-auto px-4">
        <h3 className="text-[11px] font-medium text-slate-500 uppercase tracking-wider mb-3 px-2">
          Documentos ({documents.length})
        </h3>
        {documents.length === 0 ? (
          <div className="text-center py-8">
            <div className="w-12 h-12 mx-auto mb-3 rounded-2xl bg-slate-800/30 flex items-center justify-center">
              <svg className="w-6 h-6 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <p className="text-sm text-slate-600">Sin documentos</p>
          </div>
        ) : (
          <ul className="space-y-2">
            {documents.map((doc, i) => (
              <li
                key={i}
                className="flex items-center gap-3 p-3 rounded-2xl hover:bg-slate-800/40 transition-all duration-200 group cursor-pointer"
              >
                <div className="w-10 h-10 bg-gradient-to-br from-slate-800 to-slate-800/50 rounded-xl flex items-center justify-center flex-shrink-0 group-hover:from-orange-500/20 group-hover:to-orange-600/10 transition-all duration-200">
                  <svg className="w-5 h-5 text-slate-400 group-hover:text-orange-400 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                  </svg>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-slate-300 truncate">{doc.name}</p>
                  <p className="text-xs text-slate-600">{doc.chunks} chunks indexados</p>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

    </aside>
  );
}
