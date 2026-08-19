export type Role = "user" | "assistant" | "system";

export interface MessageCitation {
  id: string;
  source: string; // e.g. "NICE NG136", "WHO 2021", "NICE CG181"
  section: string; // e.g. "Section 1.1.1 - First-line drug classes"
  page?: string | number; // e.g. "p. 14"
  quote?: string;
  relevanceScore?: number; // 0 to 1
  strength?: "Strong" | "Conditional" | "Consider" | "Not Recommended";
}

export interface RagMetrics {
  precisionAtK?: number;
  faithfulnessScore?: number;
  retrievalLatencyMs?: number;
  generationLatencyMs?: number;
  totalLatencyMs?: number;
  tokensUsed?: number;
  embeddingModel?: string;
  llmModel?: string;
}

export interface RetrievedChunk {
  id: string;
  title: string;
  content: string;
  source: string;
  section: string;
  page: string;
  similarityScore: number; // 0.0 - 1.0
  recommendationStrength?: string;
}

export interface TranslationMeta {
  originalQuery: string;
  detectedLang: "ar" | "en";
  translatedQuery: string;
  translationModel: string;
  latencyMs: number;
}

export interface ChatMessage {
  id: string;
  role: Role;
  content: string;
  timestamp: number;
  citations?: MessageCitation[];
  metrics?: RagMetrics;
  retrievedChunks?: RetrievedChunk[];
  translation?: TranslationMeta;
  confidenceScore?: number; // e.g. 0.94 (94% Grounded)
  isInsufficientEvidence?: boolean;
  guidelineComparison?: {
    whoStance: string;
    niceStance: string;
    consensus: string;
  };
}

export interface ChatSession {
  id: string;
  title: string;
  createdAt: number;
  updatedAt: number;
  messages: ChatMessage[];
  pinned?: boolean;
}
