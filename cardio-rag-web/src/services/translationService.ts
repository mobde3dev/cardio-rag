import { TranslationMeta } from "@/types/chat";

export const isArabicText = (text: string): boolean => {
  const arabicPattern = /[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]/;
  return arabicPattern.test(text);
};

export async function translateQueryIfNeeded(
  query: string,
  model: string = "openai/gpt-oss-20b",
  apiKey?: string
): Promise<TranslationMeta | null> {
  const isAr = isArabicText(query);
  if (!isAr) {
    return {
      originalQuery: query,
      detectedLang: "en",
      translatedQuery: query,
      translationModel: "direct",
      latencyMs: 0,
    };
  }

  const startTime = Date.now();
  try {
    const res = await fetch("/api/translate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, model, apiKey }),
    });

    if (!res.ok) {
      throw new Error(`Translation failed with status ${res.status}`);
    }

    const data = await res.json();
    return {
      originalQuery: query,
      detectedLang: "ar",
      translatedQuery: data.translatedQuery || query,
      translationModel: model,
      latencyMs: Date.now() - startTime,
    };
  } catch (error) {
    console.warn("Translation fallback to original text:", error);
    return {
      originalQuery: query,
      detectedLang: "ar",
      translatedQuery: query,
      translationModel: "fallback",
      latencyMs: Date.now() - startTime,
    };
  }
}
