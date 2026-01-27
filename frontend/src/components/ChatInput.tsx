import { useState } from "react";

interface ChatInputProps {
  onSend: (message: string) => void;
  loading: boolean;
}

export function ChatInput({ onSend, loading }: ChatInputProps) {
  const [input, setInput] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;
    onSend(input.trim());
    setInput("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="relative">
      <div className="relative bg-gradient-to-b from-slate-800 to-slate-800/90 rounded-[28px] border border-slate-700/50 focus-within:border-slate-600/70 focus-within:shadow-lg focus-within:shadow-slate-900/50 transition-all duration-300">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Escribe tu pregunta..."
          disabled={loading}
          rows={1}
          className="w-full px-6 py-4 pr-16 bg-transparent resize-none focus:outline-none placeholder-slate-500 disabled:opacity-50 text-sm"
          style={{ minHeight: "60px", maxHeight: "200px" }}
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="absolute right-3 bottom-3 w-11 h-11 flex items-center justify-center rounded-2xl bg-gradient-to-br from-orange-500 to-orange-600 hover:from-orange-400 hover:to-orange-500 disabled:from-slate-700 disabled:to-slate-700 disabled:text-slate-500 transition-all duration-200 shadow-lg hover:shadow-orange-500/25 hover:scale-105 active:scale-95"
        >
          {loading ? (
            <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
          ) : (
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M12 5l7 7-7 7" />
            </svg>
          )}
        </button>
      </div>
      <p className="text-[11px] text-slate-600 mt-3 text-center">
        Presiona Enter para enviar
      </p>
    </form>
  );
}
