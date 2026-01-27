import ReactMarkdown from "react-markdown";

interface ChatMessageProps {
  role: "user" | "assistant";
  content: string;
  sources?: string[];
}

export function ChatMessage({ role, content, sources }: ChatMessageProps) {
  const isUser = role === "user";

  return (
    <div className={`flex gap-4 ${isUser ? "flex-row-reverse" : ""}`}>
      {/* Avatar */}
      {isUser ? (
        <div className="w-9 h-9 rounded-full bg-gradient-to-br from-slate-600 to-slate-700 flex items-center justify-center flex-shrink-0 shadow-lg">
          <svg className="w-4 h-4 text-slate-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
          </svg>
        </div>
      ) : (
        <div className="relative flex-shrink-0">
          <div className="absolute inset-0 bg-orange-500/20 rounded-full blur-md" />
          <img 
            src="/logo.png" 
            alt="Agent" 
            className="relative w-9 h-9 rounded-full object-cover ring-2 ring-orange-500/30 shadow-lg" 
          />
        </div>
      )}

      {/* Content */}
      <div className={`flex-1 max-w-[80%] ${isUser ? "text-right" : ""}`}>
        <div
          className={`inline-block text-left shadow-lg ${
            isUser
              ? "bg-gradient-to-br from-slate-700 to-slate-700/90 text-slate-100 rounded-3xl rounded-tr-lg px-5 py-3.5"
              : "bg-gradient-to-br from-slate-800/80 to-slate-800/60 border border-slate-700/30 text-slate-200 rounded-3xl rounded-tl-lg px-5 py-4"
          }`}
        >
          {isUser ? (
            <p className="text-sm leading-relaxed">{content}</p>
          ) : (
            <div className="prose prose-invert prose-sm max-w-none prose-p:leading-relaxed prose-p:text-slate-300 prose-headings:text-slate-200 prose-strong:text-slate-200 prose-li:text-slate-300 prose-ul:my-2 prose-ol:my-2">
              <ReactMarkdown>{content}</ReactMarkdown>
            </div>
          )}
        </div>

        {/* Sources */}
        {sources && sources.length > 0 && (
          <div className="mt-2.5 inline-flex items-center gap-2 text-xs text-slate-500 bg-slate-800/30 px-3 py-1.5 rounded-full">
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
            </svg>
            <span>{sources.join(", ")}</span>
          </div>
        )}
      </div>
    </div>
  );
}
