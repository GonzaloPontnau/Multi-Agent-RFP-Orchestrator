import { useState } from "react";

interface Document {
  name: string;
  chunks: number;
  uploadedAt: Date;
}

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
    <aside className="w-72 bg-slate-900 border-r border-slate-800 flex flex-col">
      {/* Logo */}
      <div className="p-5 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg flex items-center justify-center">
            <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <div>
            <h1 className="font-semibold text-white">RFP Orchestrator</h1>
            <p className="text-xs text-slate-500">Multi-Agent System</p>
          </div>
        </div>
      </div>

      {/* Upload Area */}
      <div className="p-4">
        <label
          className={`block border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all ${
            dragOver
              ? "border-blue-500 bg-blue-500/10"
              : "border-slate-700 hover:border-slate-600 hover:bg-slate-800/50"
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
            <div className="flex flex-col items-center gap-2">
              <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
              <span className="text-sm text-slate-400">Procesando...</span>
            </div>
          ) : (
            <>
              <svg className="w-8 h-8 mx-auto text-slate-500 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              <p className="text-sm text-slate-400">Arrastra un PDF aqui</p>
              <p className="text-xs text-slate-600 mt-1">o haz click para seleccionar</p>
            </>
          )}
        </label>
      </div>

      {/* Documents List */}
      <div className="flex-1 overflow-y-auto">
        <div className="px-4 py-2">
          <h3 className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-3">
            Documentos ({documents.length})
          </h3>
          {documents.length === 0 ? (
            <p className="text-sm text-slate-600 text-center py-4">
              Sin documentos
            </p>
          ) : (
            <ul className="space-y-1">
              {documents.map((doc, i) => (
                <li
                  key={i}
                  className="flex items-center gap-3 p-3 rounded-lg hover:bg-slate-800/50 transition-colors group"
                >
                  <div className="w-8 h-8 bg-slate-800 rounded-lg flex items-center justify-center flex-shrink-0">
                    <svg className="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                    </svg>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-slate-300 truncate">{doc.name}</p>
                    <p className="text-xs text-slate-600">{doc.chunks} chunks</p>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-slate-800">
        <div className="flex items-center gap-2 text-xs text-slate-600">
          <div className="w-2 h-2 bg-green-500 rounded-full" />
          <span>Sistema activo</span>
        </div>
      </div>
    </aside>
  );
}
