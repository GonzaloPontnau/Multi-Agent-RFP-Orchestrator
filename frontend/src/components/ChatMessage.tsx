import ReactMarkdown from "react-markdown";

interface ChatMessageProps {
  role: "user" | "assistant";
  content: string;
  sources?: string[];
}

export function ChatMessage({ role, content, sources }: ChatMessageProps) {
  const isUser = role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-3 ${
          isUser
            ? "bg-primary text-white rounded-br-md"
            : "bg-slate-700 text-slate-100 rounded-bl-md"
        }`}
      >
        {isUser ? (
          <p>{content}</p>
        ) : (
          <div className="prose prose-invert prose-sm max-w-none">
            <ReactMarkdown>{content}</ReactMarkdown>
          </div>
        )}

        {sources && sources.length > 0 && (
          <div className="mt-2 pt-2 border-t border-slate-600">
            <p className="text-xs text-slate-400">
              Fuentes: {sources.join(", ")}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
