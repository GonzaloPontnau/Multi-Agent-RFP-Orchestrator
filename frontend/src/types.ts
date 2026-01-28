export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: string[];
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
}
