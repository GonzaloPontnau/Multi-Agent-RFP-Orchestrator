import ReactMarkdown from "react-markdown";
import type { AgentMetadata, RiskLevel } from "../types";

interface ChatMessageProps {
  role: "user" | "assistant";
  content: string;
  sources?: string[];
  agentMetadata?: AgentMetadata;
}

const DOMAIN_LABELS: Record<string, { label: string; color: string }> = {
  legal: { label: "Legal", color: "text-purple-400 bg-purple-500/10 border-purple-500/20" },
  technical: { label: "Tecnico", color: "text-blue-400 bg-blue-500/10 border-blue-500/20" },
  financial: { label: "Financiero", color: "text-green-400 bg-green-500/10 border-green-500/20" },
  timeline: { label: "Cronograma", color: "text-amber-400 bg-amber-500/10 border-amber-500/20" },
  requirements: { label: "Requisitos", color: "text-cyan-400 bg-cyan-500/10 border-cyan-500/20" },
  general: { label: "General", color: "text-slate-400 bg-slate-500/10 border-slate-500/20" },
  quantitative: { label: "Cuantitativo", color: "text-pink-400 bg-pink-500/10 border-pink-500/20" },
};

const RISK_COLORS: Record<RiskLevel, { bg: string; text: string; label: string }> = {
  low: { bg: "bg-green-500/20", text: "text-green-400", label: "Bajo" },
  medium: { bg: "bg-yellow-500/20", text: "text-yellow-400", label: "Medio" },
  high: { bg: "bg-orange-500/20", text: "text-orange-400", label: "Alto" },
  critical: { bg: "bg-red-500/20", text: "text-red-400", label: "Critico" },
};

const COMPLIANCE_LABELS: Record<string, { color: string; label: string }> = {
  approved: { color: "text-green-400", label: "Verificado" },
  pending: { color: "text-yellow-400", label: "Requiere Revisión" },
  rejected: { color: "text-red-400", label: "Con Errores" },
};

export function ChatMessage({ role, content, sources, agentMetadata }: ChatMessageProps) {
  const isUser = role === "user";
  const domainInfo = agentMetadata ? DOMAIN_LABELS[agentMetadata.domain] || DOMAIN_LABELS.general : null;

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
        {/* Agent Metadata Badge */}
        {!isUser && agentMetadata && domainInfo && (
          <div className="mb-2 flex items-center gap-2 flex-wrap">
            <span className={`inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full border ${domainInfo.color}`}>
              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
              {domainInfo.label}
            </span>
            <span className="text-xs text-slate-500">
              {agentMetadata.documents_retrieved} docs / {agentMetadata.documents_filtered} relevantes
            </span>
            {agentMetadata.revision_count > 0 && (
              <span className="text-xs text-amber-500/80">
                {agentMetadata.revision_count} revision{agentMetadata.revision_count > 1 ? "es" : ""}
              </span>
            )}
            {/* Risk Sentinel Badge */}
            {agentMetadata.risk_assessment && (
              <>
                <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full ${RISK_COLORS[agentMetadata.risk_assessment.risk_level].bg} ${RISK_COLORS[agentMetadata.risk_assessment.risk_level].text}`}>
                  <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
                  </svg>
                  Riesgo: {RISK_COLORS[agentMetadata.risk_assessment.risk_level].label}
                </span>
                <span className={`text-xs ${COMPLIANCE_LABELS[agentMetadata.risk_assessment.compliance_status]?.color || "text-slate-400"}`}>
                  {COMPLIANCE_LABELS[agentMetadata.risk_assessment.compliance_status]?.label || agentMetadata.risk_assessment.compliance_status}
                </span>
              </>
            )}
            {!agentMetadata.risk_assessment && (
              <span className={`text-xs ${agentMetadata.audit_result === "pass" ? "text-green-500/80" : "text-red-500/80"}`}>
                {agentMetadata.audit_result === "pass" ? "OK" : "Refinado"}
              </span>
            )}
          </div>
        )}

        <div
          className={`inline-block text-left shadow-lg ${isUser
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

        {/* QuanT Chart */}
        {!isUser && agentMetadata?.quant_analysis?.chart_base64 && (
          <div className="mt-3 p-3 bg-slate-800/50 rounded-xl border border-slate-700/30">
            <div className="flex items-center gap-2 mb-2 text-xs text-pink-400">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
              <span>Analisis QuanT</span>
              {agentMetadata.quant_analysis.chart_type && (
                <span className="text-slate-500">({agentMetadata.quant_analysis.chart_type})</span>
              )}
            </div>
            <img
              src={`data:image/png;base64,${agentMetadata.quant_analysis.chart_base64}`}
              alt="Grafico de analisis"
              className="rounded-lg max-w-full h-auto"
            />
            {agentMetadata.quant_analysis.data_quality && (
              <div className="mt-2 text-xs text-slate-500">
                Calidad de datos: {agentMetadata.quant_analysis.data_quality}
              </div>
            )}
          </div>
        )}

        {/* Risk Sentinel Issues */}
        {!isUser && agentMetadata?.risk_assessment?.issues && agentMetadata.risk_assessment.issues.length > 0 && (
          <div className="mt-3 p-3 bg-slate-800/50 rounded-xl border border-orange-500/20">
            <div className="flex items-center gap-2 mb-2 text-xs text-orange-400">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <span>Observaciones de Risk Sentinel</span>
            </div>
            <ul className="text-xs text-slate-400 space-y-1">
              {agentMetadata.risk_assessment.issues.map((issue, idx) => (
                <li key={idx} className="flex items-start gap-2">
                  <span className="text-orange-400 mt-0.5">-</span>
                  <span>{issue}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

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
