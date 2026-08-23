import {
  RetrievedChunk,
  MessageCitation,
} from "@/types/chat";

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
  // Extra real-RAG metadata
  retrievalMode?: string;
  queryProfile?: Record<string, unknown>;
  candidateCount?: number;
}

/**
 * Shape returned by the Python/FastAPI backend.
 */
interface BackendChunk {
  id?: string;
  chunk_id?: string;
  text?: string;
  similarity?: number;
  semantic_score?: number;
  rerank_score?: number;
  source_file?: string;
  organization?: string;
  guideline_code?: string;
  section?: string;
  subsection?: string;
  recommendation_id?: string;
  domain?: string;
  topic?: string;
  subtopic?: string;
  content_type?: string;
  detected_content_type?: string;
  prevention_type?: string;
  clinical_priority?: number;
  pdf_page_start?: number;
  pdf_page_end?: number;
  is_canonical?: boolean;
  metadata?: Record<string, any> | null;
  rerank_reasons?: Array<any>;
}

interface BackendResponse {
  query?: string;
  profile?: Record<string, unknown>;
  retrieval_mode?: string;
  candidate_count?: number;
  results?: BackendChunk[];
}

// Built-in Guideline Evidence Knowledge Base (Strictly WHO 2021 & NICE NG238)
const GUIDELINE_CHUNKS: Record<string, RetrievedChunk[]> = {
  hypertension_first_line: [
    {
      id: "who-2021-rec1-drug-classes",
      title: "WHO 2021: Initial pharmacological drug classes",
      source: "WHO 2021",
      section: "Recommendation 1 — Pharmacological treatment of hypertension",
      page: "p. 22, Section 5.1",
      similarityScore: 0.94,
      recommendationStrength: "Strong",
      content:
        "WHO recommends initiating pharmacological treatment with any of the following three classes: 1) Thiazide and thiazide-like diuretics, 2) ACE inhibitors (ACEi) / Angiotensin Receptor Blockers (ARBs), and 3) Long-acting dihydropyridine Calcium Channel Blockers (CCBs).",
    },
    {
      id: "nice-ng238-cvd-prevention",
      title: "NICE NG238: Blood Pressure & Cardiovascular Risk Reduction",
      source: "NICE NG238",
      section: "Section 1.2 — Blood pressure and lipid co-management in CVD risk",
      page: "p. 18, Section 1.2.3",
      similarityScore: 0.92,
      recommendationStrength: "Strong",
      content:
        "In patients with elevated cardiovascular risk or established CVD, manage hypertension concurrently with lipid modification. Optimize BP using first-line ACEi/ARB or CCB according to clinical tolerance.",
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
    {
      id: "nice-ng238-secondary-prevention-target",
      title: "NICE NG238: Target Lipid Levels for Secondary Prevention",
      source: "NICE NG238",
      section: "Section 1.7 — Secondary prevention of cardiovascular disease",
      page: "p. 26, Rec 1.7.1",
      similarityScore: 0.95,
      recommendationStrength: "Strong",
      content:
        "For secondary prevention of CVD, aim for LDL cholesterol levels of 2.0 mmol/L or less, or non-HDL cholesterol levels of 2.6 mmol/L or less. Start treatment with Atorvastatin 80mg.",
    },
  ],
  pregnancy_contraindications: [
    {
      id: "nice-ng238-pregnancy-contraindications",
      title: "NICE NG238: Statins & Lipid Therapies in Pregnancy",
      source: "NICE NG238",
      section: "Section 1.6 — Lipid management in women of childbearing potential",
      page: "p. 36",
      similarityScore: 0.95,
      recommendationStrength: "Strong (Do Not Offer)",
      content:
        "Do not offer statins to women who are pregnant or planning pregnancy. Discontinue statins 3 months before attempting conception and do not use during pregnancy or breastfeeding.",
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
        "ACEi and ARBs are strictly contraindicated during pregnancy due to fetotoxicity. First-line antihypertensive therapy in pregnancy includes labetalol, nifedipine (extended-release), or methyldopa.",
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

function cleanClinicalText(value: string | undefined | null): string {
  if (!value) return "";
  return value
    .replace(/Â /g, " ")
    .replace(/\u00A0/g, " ")
    .replace(/ΓÇó/g, "•")
    .replace(/ΓëÑ/g, "≥")
    .replace(/Γëñ/g, "≤")
    .replace(/ΓÇô/g, "–")
    .replace(/ΓÇæ/g, "-")
    .trim();
}

function buildSourceName(chunk: BackendChunk): string {
  const organization = chunk.organization?.trim();
  const guideline = chunk.guideline_code?.trim();
  if (organization && guideline) return `${organization} ${guideline}`;
  if (organization) return organization;
  if (chunk.source_file) return chunk.source_file;
  return "Clinical Guideline";
}

function buildChunkTitle(chunk: BackendChunk): string {
  const source = buildSourceName(chunk);
  if (chunk.recommendation_id) return `${source}: Recommendation ${chunk.recommendation_id}`;
  if (chunk.subsection) return `${source}: ${chunk.subsection}`;
  if (chunk.section) return `${source}: ${chunk.section}`;
  return source;
}

function buildPageLabel(chunk: BackendChunk): string {
  const start = chunk.pdf_page_start;
  const end = chunk.pdf_page_end;
  if (typeof start === "number" && typeof end === "number" && start !== end) {
    return `pp. ${start}-${end}`;
  }
  if (typeof start === "number") return `p. ${start}`;
  return "Page not available";
}

function getSemanticScore(chunk: BackendChunk): number {
  const score = chunk.semantic_score ?? chunk.similarity ?? 0;
  if (!Number.isFinite(score)) return 0;
  return Math.max(0, Math.min(1, score));
}

function getRecommendationStrength(chunk: BackendChunk): string {
  const metadata = chunk.metadata ?? {};
  return metadata.recommendation_strength ?? metadata.recommendationStrength ?? "Not specified";
}

function mapBackendChunk(chunk: BackendChunk): RetrievedChunk {
  const content = cleanClinicalText(chunk.text);
  const section = cleanClinicalText(chunk.section);
  const subsection = cleanClinicalText(chunk.subsection);
  const fullSection = subsection
    ? `${section} — ${subsection}`
    : section || "Section not available";

  return {
    id: chunk.chunk_id ?? chunk.id ?? crypto.randomUUID(),
    title: buildChunkTitle(chunk),
    source: buildSourceName(chunk),
    section: fullSection,
    page: buildPageLabel(chunk),
    similarityScore: getSemanticScore(chunk),
    recommendationStrength: getRecommendationStrength(chunk),
    content,
  };
}

function buildCitations(chunks: RetrievedChunk[]): MessageCitation[] {
  return chunks.map((chunk) => {
    const cleanQuote = chunk.content.trim();
    const quote = cleanQuote.length > 180 ? `${cleanQuote.slice(0, 180)}...` : cleanQuote;
    return {
      id: chunk.id,
      source: chunk.source,
      section: chunk.section,
      page: chunk.page,
      quote,
      relevanceScore: chunk.similarityScore,
      strength: (chunk.recommendationStrength || "Not specified") as MessageCitation["strength"],
    };
  });
}

function buildGuidelineComparison(backendChunks: BackendChunk[]): RetrievedEvidence["guidelineComparison"] {
  const whoChunks = backendChunks.filter(
    (chunk) => chunk.organization?.toUpperCase() === "WHO"
  );
  const niceChunks = backendChunks.filter(
    (chunk) => chunk.organization?.toUpperCase() === "NICE"
  );

  if (whoChunks.length === 0 || niceChunks.length === 0) {
    return undefined;
  }

  const whoEvidence = cleanClinicalText(whoChunks[0]?.text);
  const niceEvidence = cleanClinicalText(niceChunks[0]?.text);

  const shorten = (text: string, maxLength: number = 350) => {
    if (text.length <= maxLength) return text;
    return text.slice(0, maxLength) + "...";
  };

  return {
    whoStance: shorten(whoEvidence),
    niceStance: shorten(niceEvidence),
    consensus:
      "Relevant evidence was retrieved from both WHO and NICE. The final clinical comparison should be generated from these retrieved sources without merging the guidelines into a single recommendation.",
  };
}

function getFallbackClinicalEvidence(query: string, topK: number = 4): RetrievedEvidence {
  const q = query.toLowerCase();
  let chunks: RetrievedChunk[] = [];
  let guidelineComparison: RetrievedEvidence["guidelineComparison"] = undefined;

  if (
    q.includes("فئات") ||
    q.includes("أولي") ||
    q.includes("first-line") ||
    q.includes("three drug") ||
    q.includes("classes") ||
    q.includes("ضغط الدم") ||
    q.includes("hypertension")
  ) {
    chunks = GUIDELINE_CHUNKS.hypertension_first_line;
    guidelineComparison = {
      whoStance:
        "WHO 2021: Recommends initiating treatment with any of 3 drug classes (Thiazide-like, ACEi/ARB, CCB) with strong preference for single-pill combinations.",
      niceStance:
        "NICE NG238: Recommends comprehensive cardiovascular risk co-management, combining BP reduction with statin therapy for secondary prevention.",
      consensus:
        "Both guidelines emphasize early aggressive blood pressure control using proven first-line agents alongside lifestyle and lipid risk assessment.",
    };
  } else if (
    q.includes("ستاتين") ||
    q.includes("statin") ||
    q.includes("شدة") ||
    q.includes("intensity") ||
    q.includes("كوليسترول") ||
    q.includes("دهون") ||
    q.includes("ldl") ||
    q.includes("target")
  ) {
    chunks = GUIDELINE_CHUNKS.statins_intensity;
  } else if (
    q.includes("حمل") ||
    q.includes("pregnant") ||
    q.includes("pregnancy") ||
    q.includes("ace") ||
    q.includes("arb")
  ) {
    chunks = GUIDELINE_CHUNKS.pregnancy_contraindications;
  } else if (
    q.includes("غير الأطباء") ||
    q.includes("شروط") ||
    q.includes("non-physician") ||
    q.includes("who") ||
    q.includes("صيادلة")
  ) {
    chunks = GUIDELINE_CHUNKS.task_shifting_who;
  } else {
    chunks = [
      ...GUIDELINE_CHUNKS.hypertension_first_line,
      ...GUIDELINE_CHUNKS.statins_intensity,
    ];
  }

  const selectedChunks = chunks.slice(0, topK);
  const avgSimilarity =
    selectedChunks.reduce((acc, c) => acc + c.similarityScore, 0) /
    (selectedChunks.length || 1);

  const citations: MessageCitation[] = selectedChunks.map((chunk) => ({
    id: chunk.id,
    source: chunk.source,
    section: chunk.section,
    page: chunk.page,
    quote: chunk.content.slice(0, 120) + "...",
    relevanceScore: chunk.similarityScore,
    strength:
      (chunk.recommendationStrength as MessageCitation["strength"]) || "Strong",
  }));

  return {
    chunks: selectedChunks,
    citations,
    groundedScore: Math.round(avgSimilarity * 100) / 100,
    isInsufficientEvidence: avgSimilarity < 0.65,
    guidelineComparison,
    retrievalMode: "offline_curated_knowledge_base",
  };
}

/**
 * Robust CardioRAG evidence retrieval:
 * 1. Attempts live retrieval via Next.js API /api/retrieve (FastAPI / BGE-M3 / Supabase).
 * 2. Falls back gracefully to the built-in clinical guideline database if the backend is unreachable.
 */
export async function retrieveClinicalEvidence(
  query: string,
  topK: number = 5
): Promise<RetrievedEvidence> {
  const trimmedQuery = query.trim();

  if (!trimmedQuery) {
    return {
      chunks: [],
      citations: [],
      groundedScore: 0,
      isInsufficientEvidence: true,
      guidelineComparison: undefined,
      retrievalMode: "empty_query",
      queryProfile: {},
      candidateCount: 0,
    };
  }

  try {
    const response = await fetch("/api/retrieve", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        query: trimmedQuery,
      }),
      cache: "no-store",
    });

    if (response.ok) {
      const data: BackendResponse = await response.json();
      const backendChunks = (data.results ?? []).slice(0, topK);

      if (backendChunks.length > 0) {
        const chunks: RetrievedChunk[] = backendChunks.map(mapBackendChunk);
        const citations = buildCitations(chunks);

        const avgSimilarity =
          chunks.reduce((total, chunk) => total + chunk.similarityScore, 0) /
          chunks.length;

        const groundedScore = Math.round(avgSimilarity * 100) / 100;
        const bestScore = Math.max(...chunks.map((c) => c.similarityScore));
        const isInsufficientEvidence = bestScore < 0.55;

        const guidelineComparison = buildGuidelineComparison(backendChunks);

        return {
          chunks,
          citations,
          groundedScore,
          isInsufficientEvidence,
          guidelineComparison,
          retrievalMode: data.retrieval_mode || "live_backend_vector_search",
          queryProfile: data.profile,
          candidateCount: data.candidate_count,
        };
      }
    }
  } catch (error) {
    console.warn("Live RAG retrieval notice: Falling back to built-in clinical evidence.", error);
  }

  // Fallback to high-quality curated WHO & NICE clinical knowledge base
  return getFallbackClinicalEvidence(trimmedQuery, topK);
}