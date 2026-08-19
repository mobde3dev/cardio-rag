import { RetrievedChunk, MessageCitation, RagMetrics } from "./chat";

export interface RagResponsePayload {
  answer: string;
  citations: MessageCitation[];
  chunks: RetrievedChunk[];
  metrics: RagMetrics;
  confidenceScore: number;
  isInsufficientEvidence: boolean;
  translatedQuery?: string;
}

export interface GuidelineMetadata {
  id: string;
  name: string;
  code: string;
  organization: "NICE" | "WHO" | "ESC" | "ACC/AHA";
  year: number;
  title: string;
  url?: string;
  scope: string;
  totalChunksCount: number;
  lastUpdated: string;
}

export interface RubricCriterion {
  id: string;
  title: string;
  titleAr: string;
  maxPoints: number;
  description: string;
  descriptionAr: string;
  checks: string[];
  checksAr: string[];
}
