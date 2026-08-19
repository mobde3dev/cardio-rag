export interface ModelOption {
  id: string;
  name: string;
  provider: string;
  contextWindow: number;
  description: string;
  descriptionAr: string;
  badge?: string;
  isDefault?: boolean;
  recommendedFor?: string;
}

export interface AppSettings {
  groqApiKey: string;
  selectedModel: string;
  translationModel: string;
  temperature: number;
  topK: number;
  confidenceThreshold: number; // 0.0 - 1.0
  autoTranslateArabic: boolean;
  streamResponse: boolean;
  soundEffects: boolean;
}
