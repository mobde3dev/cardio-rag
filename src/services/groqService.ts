import { ChatMessage, RetrievedChunk } from "@/types/chat";
import { AppSettings } from "@/types/settings";

export interface GroqChatPayload {
  messages: { role: "system" | "user" | "assistant"; content: string }[];
  model: string;
  temperature?: number;
  max_tokens?: number;
  apiKey?: string;
}

export const groqService = {
  async sendClinicalPrompt({
    query,
    retrievedChunks,
    model,
    temperature = 0.15,
    userLanguage = "ar",
    apiKey,
  }: {
    query: string;
    retrievedChunks: RetrievedChunk[];
    model: string;
    temperature?: number;
    userLanguage: "ar" | "en";
    apiKey?: string;
  }): Promise<{ content: string; tokensUsed: number }> {
    const contextText = retrievedChunks
      .map(
        (c, idx) =>
          `[Evidence Document ${idx + 1}]:\nSource: ${c.source} (${c.section}, ${c.page})\nContent: ${c.content}\n`
      )
      .join("\n---\n");

    const systemPrompt = `You are CardioRAG, an evidence-based clinical decision support AI assistant specialized in cardiology clinical guidelines (NICE NG136, WHO 2021, NICE CG181/NG238).

GROUNDING RULES:
1. Base your answer strictly and exclusively on the provided Evidence Documents.
2. Format your response cleanly in ${userLanguage === "ar" ? "Arabic" : "English"}.
3. Structure your response clearly with:
   - Direct Clinical Answer / الإجابة السريرية المباشرة
   - Specific Guideline Citations / الاستشهادات الإرشادية المحددة (Doc, Section, Page)
   - Recommendation Strength / قوة التوصية (e.g. Strong / Conditional / Offer / Consider)
   - Clinical Safety & Monitoring Note / ملاحظة الأمان والمتابعة السريرية
4. If evidence is missing or insufficient, state clearly that guidance is not indexed and avoid speculative clinical advice.
5. Use markdown tables, bold headings, and bullet points for high legibility.`;

    const userPrompt = `Clinical Evidence Documents:\n${contextText}\n\nClinical Question:\n${query}`;

    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        messages: [
          { role: "system", content: systemPrompt },
          { role: "user", content: userPrompt },
        ],
        model,
        temperature,
        apiKey,
      }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || `Server error ${res.status}`);
    }

    const data = await res.json();
    return {
      content: data.content,
      tokensUsed: data.tokensUsed || 350,
    };
  },
};
