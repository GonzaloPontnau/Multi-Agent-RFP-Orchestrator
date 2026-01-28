export type AgentDomain = "legal" | "technical" | "financial" | "timeline" | "requirements" | "general" | "quantitative";

export type RiskLevel = "low" | "medium" | "high" | "critical";
export type ComplianceStatus = "approved" | "pending" | "rejected";

export interface QuantAnalysis {
  chart_base64: string | null;
  chart_type: string | null;
  insights: string;
  data_quality: string;
}

export interface RiskAssessment {
  risk_level: RiskLevel;
  compliance_status: ComplianceStatus;
  issues: string[];
  gate_passed: boolean;
}

export interface AgentMetadata {
  domain: AgentDomain;
  specialist_used: string;
  documents_retrieved: number;
  documents_filtered: number;
  revision_count: number;
  audit_result: string;
  quant_analysis?: QuantAnalysis;
  risk_assessment?: RiskAssessment;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: string[];
  agentMetadata?: AgentMetadata;
}

export interface Document {
  name: string;
  chunks: number;
  uploadedAt: Date;
}

export interface IngestResponse {
  status: string;
  filename: string;
  chunks_processed: number;
}

export interface ChatResponse {
  answer: string;
  sources: string[];
  agent_metadata: AgentMetadata;
}
