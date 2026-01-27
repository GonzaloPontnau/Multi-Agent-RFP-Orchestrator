import { useRef, useState, useEffect } from "react";
import { ChatInput } from "./components/ChatInput";
import { ChatMessage } from "./components/ChatMessage";
import { PromptSuggestions } from "./components/PromptSuggestions";
import { Sidebar } from "./components/Sidebar";
import { useRFP } from "./hooks/useRFP";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: string[];
}

interface Document {
  name: string;
  chunks: number;
  uploadedAt: Date;
}

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
    <div className="h-screen bg-slate-950 text-slate-100 flex overflow-hidden">
      {/* Sidebar */}
      <Sidebar documents={documents} onUpload={handleUpload} loading={loading} />

      {/* Main Content */}
      <main className="flex-1 flex flex-col min-w-0">
        {/* Error Banner */}
        {error && (
          <div className="mx-6 mt-4 px-4 py-3 bg-red-950/50 border border-red-900/50 rounded-xl flex items-center justify-between">
            <div className="flex items-center gap-3">
              <svg className="w-5 h-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span className="text-sm text-red-300">{error}</span>
            </div>
            <button onClick={clearError} className="p-1 hover:bg-red-900/30 rounded-lg transition-colors">
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
              <div className="max-w-3xl mx-auto py-8 px-6 space-y-6">
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
                    <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center flex-shrink-0">
                      <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                      </svg>
                    </div>
                    <div className="bg-slate-800/50 border border-slate-800 rounded-2xl px-4 py-3">
                      <div className="flex items-center gap-1">
                        <div className="w-2 h-2 bg-slate-500 rounded-full animate-pulse" />
                        <div className="w-2 h-2 bg-slate-500 rounded-full animate-pulse" style={{ animationDelay: "0.2s" }} />
                        <div className="w-2 h-2 bg-slate-500 rounded-full animate-pulse" style={{ animationDelay: "0.4s" }} />
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
        <div className="border-t border-slate-800/50 bg-slate-900/50 backdrop-blur-sm">
          <div className="max-w-3xl mx-auto p-6">
            <ChatInput onSend={handleSend} loading={loading} />
          </div>
        </div>
      </main>
    </div>
  );
}
