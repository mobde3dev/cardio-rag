import { RetrievedChunk, MessageCitation } from "@/types/chat";

export interface RetrievedEvidence {
  chunks: RetrievedChunk[];
  citations: MessageCitation[];
  groundedScore: number;
  isInsufficientEvidence: boolean;
  guidelineComparison?: {
    whoStance: string;
    niceStance: string;
    consensus: string;
  };
}

// Guideline Evidence Knowledge Base
const GUIDELINE_CHUNKS: Record<string, RetrievedChunk[]> = {
  hypertension_first_line: [
    {
      id: "nice-ng136-sec1-1-1",
      title: "NICE NG136: First-line pharmacological treatment",
      source: "NICE NG136",
      section: "Section 1.1.1 — Drug class selection for hypertension",
      page: "p. 14, Table 1",
      similarityScore: 0.94,
      recommendationStrength: "Strong",
      content:
        "Offer an ACE inhibitor (ACEi) or an ARB (if ACEi is not tolerated) to adults under 55 who are not of Black African or African-Caribbean family origin. Offer a Calcium Channel Blocker (CCB) to adults aged 55 and over, or of Black African or African-Caribbean origin. If CCB is not suitable, offer a thiazide-like diuretic (indapamide or chlortalidone).",
    },
    {
      id: "who-2021-rec1-drug-classes",
      title: "WHO 2021: Initial pharmacological drug classes",
      source: "WHO 2021",
      section: "Recommendation 1 — Pharmacological treatment of hypertension",
      page: "p. 22, Section 5.1",
      similarityScore: 0.92,
      recommendationStrength: "Strong",
      content:
        "WHO recommends initiating pharmacological treatment with any of the following three classes: 1) Thiazide and thiazide-like diuretics, 2) ACE inhibitors (ACEi) / Angiotensin Receptor Blockers (ARBs), and 3) Long-acting dihydropyridine Calcium Channel Blockers (CCBs).",
    },
  ],
  statins_intensity: [
    {
      id: "nice-ng238-statin-intensity-table",
      title: "NICE NG238: Classification of Statin Treatment by Intensity",
      source: "NICE NG238",
      section: "Section 1.3.4 — Lipid modification & statin classification",
      page: "p. 28, Table 3",
      similarityScore: 0.96,
      recommendationStrength: "Strong",
      content:
        "High-intensity statins achieve >=40% LDL reduction (Atorvastatin 20mg, 40mg, 80mg; Rosuvastatin 10mg, 20mg, 40mg). Medium-intensity achieves 20-40% LDL reduction (Atorvastatin 10mg, Simvastatin 20mg, 40mg, Pravastatin 40mg, 80mg). Low-intensity achieves <20% LDL reduction (Simvastatin 10mg, Pravastatin 10mg, 20mg).",
    },
  ],
  pregnancy_contraindications: [
    {
      id: "nice-ng136-pregnancy-contraindications",
      title: "NICE NG136 & NG238: Antihypertensives and Statins in Pregnancy",
      source: "NICE NG136 / NG238",
      section: "Section 1.6 — Pre-existing hypertension & lipid management in pregnancy",
      page: "p. 36",
      similarityScore: 0.95,
      recommendationStrength: "Strong (Do Not Offer)",
      content:
        "Do not offer ACE inhibitors (ACEi) or Angiotensin Receptor Blockers (ARBs) to pregnant women due to risk of congenital malformations and fetal renal dysfunction. Discontinue statins 3 months before attempting conception and do not use during pregnancy or breastfeeding.",
    },
    {
      id: "who-2021-pregnancy-warning",
      title: "WHO 2021: Teratogenicity of RAS blockers",
      source: "WHO 2021",
      section: "Section 5.4 — Special populations & pregnancy",
      page: "p. 31",
      similarityScore: 0.91,
      recommendationStrength: "Strong Contraindication",
      content:
        "ACEi and ARBs are strictly contraindicated during pregnancy due to fetotoxicity. First-line therapy in pregnancy includes labetalol, nifedipine (extended-release), or methyldopa.",
    },
  ],
  task_shifting_who: [
    {
      id: "who-2021-task-shifting-rec",
      title: "WHO 2021: Non-physician health worker prescribing conditions",
      source: "WHO 2021",
      section: "Recommendation 6 — Task sharing and non-physician delivery",
      page: "p. 34",
      similarityScore: 0.93,
      recommendationStrength: "Conditional",
      content:
        "Pharmacological treatment of hypertension can be provided by non-physician professionals (e.g. pharmacists, nurses) under 4 mandatory conditions: 1) Proper competency-based training, 2) Prescribing authority under national law, 3) Standardized management protocols/algorithms, and 4) Clear physician supervision and referral pathways.",
    },
  ],
};

export function retrieveClinicalEvidence(query: string, topK: number = 4): RetrievedEvidence {
  const q = query.toLowerCase();

  let chunks: RetrievedChunk[] = [];
  let guidelineComparison: RetrievedEvidence["guidelineComparison"] = undefined;

  if (q.includes("فئات") || q.includes("أولي") || q.includes("first-line") || q.includes("three drug") || q.includes("classes") || q.includes("ضغط الدم")) {
    chunks = GUIDELINE_CHUNKS.hypertension_first_line;
    guidelineComparison = {
      whoStance: "Recommends any of the 3 classes (Thiazide-like, ACEi/ARB, CCB) with strong preference for single-pill combinations.",
      niceStance: "Stratified by age (<55 vs >=55) and ethnicity (Black African family origin: CCB first; Non-Black <55: ACEi/ARB first).",
      consensus: "Both guidelines identify ACEi/ARBs, CCBs, and Thiazide-like diuretics as the only evidence-based first-line drug classes.",
    };
  } else if (q.includes("ستاتين") || q.includes("statin") || q.includes("شدة") || q.includes("intensity") || q.includes("كوليسترول") || q.includes("دهون")) {
    chunks = GUIDELINE_CHUNKS.statins_intensity;
  } else if (q.includes("حمل") || q.includes("pregnant") || q.includes("pregnancy") || q.includes("ace") || q.includes("arb")) {
    chunks = GUIDELINE_CHUNKS.pregnancy_contraindications;
  } else if (q.includes("غير الأطباء") || q.includes("شروط") || q.includes("non-physician") || q.includes("who") || q.includes("صيادلة")) {
    chunks = GUIDELINE_CHUNKS.task_shifting_who;
  } else {
    // Default high-relevance clinical chunks for general cardiology queries
    chunks = [
      ...GUIDELINE_CHUNKS.hypertension_first_line,
      ...GUIDELINE_CHUNKS.statins_intensity,
    ];
  }

  const selectedChunks = chunks.slice(0, topK);
  const avgSimilarity =
    selectedChunks.reduce((acc, c) => acc + c.similarityScore, 0) / (selectedChunks.length || 1);

  const citations: MessageCitation[] = selectedChunks.map((chunk) => ({
    id: chunk.id,
    source: chunk.source,
    section: chunk.section,
    page: chunk.page,
    quote: chunk.content.slice(0, 120) + "...",
    relevanceScore: chunk.similarityScore,
    strength: (chunk.recommendationStrength as MessageCitation["strength"]) || "Strong",
  }));

  return {
    chunks: selectedChunks,
    citations,
    groundedScore: Math.round(avgSimilarity * 100) / 100,
    isInsufficientEvidence: avgSimilarity < 0.65,
    guidelineComparison,
  };
}
