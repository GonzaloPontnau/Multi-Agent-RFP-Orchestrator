import { useRef, useState, useEffect } from "react";
import { ChatInput } from "./components/ChatInput";
import { ChatMessage } from "./components/ChatMessage";
import { PromptSuggestions } from "./components/PromptSuggestions";
import { Sidebar } from "./components/Sidebar";
import { useRFP } from "./hooks/useRFP";
import type { Document, Message } from "./types";

export default function App() {
  const { loading, error, uploadDocument, askQuestion, clearError } = useRFP();
  const [messages, setMessages] = useState<Message[]>([]);
  const [documents, setDocuments] = useState<Document[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleUpload = async (file: File) => {
    const result = await uploadDocument(file);
    if (result) {
      setDocuments((prev) => [
        ...prev,
        {
          name: file.name,
          chunks: result.chunks_processed,
          uploadedAt: new Date(),
        },
      ]);
    }
    return result;
  };

  const handleSend = async (question: string) => {
    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: question,
    };
    setMessages((prev) => [...prev, userMessage]);

    const response = await askQuestion(question);
    if (response) {
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: response.answer,
        sources: response.sources,
      };
      setMessages((prev) => [...prev, assistantMessage]);
    }
  };

  return (
    <div className="h-screen bg-gradient-to-br from-slate-950 via-slate-950 to-slate-900 text-slate-100 flex overflow-hidden">
      {/* Sidebar */}
      <Sidebar documents={documents} onUpload={handleUpload} loading={loading} />

      {/* Main Content */}
      <main className="flex-1 flex flex-col min-w-0">
        {/* Error Banner */}
        {error && (
          <div className="mx-6 mt-5 px-5 py-4 bg-red-950/30 border border-red-900/30 rounded-2xl flex items-center justify-between backdrop-blur-sm">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-xl bg-red-500/20 flex items-center justify-center">
                <svg className="w-4 h-4 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <span className="text-sm text-red-300">{error}</span>
            </div>
            <button 
              onClick={clearError} 
              className="p-2 hover:bg-red-900/30 rounded-xl transition-colors"
            >
              <svg className="w-4 h-4 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        )}

        {/* Chat Area */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {messages.length === 0 ? (
            <PromptSuggestions onSelect={handleSend} />
          ) : (
            <div className="flex-1 overflow-y-auto">
              <div className="max-w-3xl mx-auto py-10 px-6 space-y-8">
                {messages.map((msg) => (
                  <ChatMessage
                    key={msg.id}
                    role={msg.role}
                    content={msg.content}
                    sources={msg.sources}
                  />
                ))}
                {loading && (
                  <div className="flex gap-4">
                    <div className="relative flex-shrink-0">
                      <div className="absolute inset-0 bg-orange-500/20 rounded-full blur-md animate-pulse" />
                      <img 
                        src="/logo.png" 
                        alt="Agent" 
                        className="relative w-9 h-9 rounded-full object-cover ring-2 ring-orange-500/30" 
                      />
                    </div>
                    <div className="bg-gradient-to-br from-slate-800/80 to-slate-800/60 border border-slate-700/30 rounded-3xl rounded-tl-lg px-5 py-4 shadow-lg">
                      <div className="flex items-center gap-1.5">
                        <div className="w-2 h-2 bg-orange-500 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                        <div className="w-2 h-2 bg-orange-500 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                        <div className="w-2 h-2 bg-orange-500 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                      </div>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>
            </div>
          )}
        </div>

        {/* Input Area */}
        <div className="border-t border-slate-800/30 bg-gradient-to-t from-slate-900/80 to-transparent backdrop-blur-sm">
          <div className="max-w-3xl mx-auto p-6 pt-5">
            <ChatInput onSend={handleSend} loading={loading} />
          </div>
        </div>
      </main>
    </div>
  );
}
