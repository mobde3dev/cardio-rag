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


/**
 * Clean occasional encoding artefacts coming from
 * extracted PDF text.
 *
 * This does NOT modify clinical meaning or numbers.
 */
function cleanClinicalText(
  value: string | undefined | null
): string {

  if (!value) {
    return "";
  }

  return value
    .replace(/Â /g, " ")
    .replace(/Â /g, " ")
    .replace(/\u00A0/g, " ")
    .replace(/ΓÇó/g, "•")
    .replace(/ΓëÑ/g, "≥")
    .replace(/Γëñ/g, "≤")
    .replace(/ΓÇô/g, "–")
    .replace(/ΓÇæ/g, "-")
    .trim();
}


/**
 * Human-readable source name.
 */
function buildSourceName(
  chunk: BackendChunk
): string {

  const organization =
    chunk.organization?.trim();

  const guideline =
    chunk.guideline_code?.trim();

  if (organization && guideline) {
    return `${organization} ${guideline}`;
  }

  if (organization) {
    return organization;
  }

  if (chunk.source_file) {
    return chunk.source_file;
  }

  return "Clinical Guideline";
}


/**
 * Human-readable title used by ChunkCard.
 */
function buildChunkTitle(
  chunk: BackendChunk
): string {

  const source =
    buildSourceName(chunk);

  if (chunk.recommendation_id) {
    return `${source}: Recommendation ${chunk.recommendation_id}`;
  }

  if (chunk.subsection) {
    return `${source}: ${chunk.subsection}`;
  }

  if (chunk.section) {
    return `${source}: ${chunk.section}`;
  }

  return source;
}


/**
 * Human-readable page label while keeping the old
 * RetrievedChunk.page string structure.
 */
function buildPageLabel(
  chunk: BackendChunk
): string {

  const start =
    chunk.pdf_page_start;

  const end =
    chunk.pdf_page_end;

  if (
    typeof start === "number" &&
    typeof end === "number" &&
    start !== end
  ) {
    return `pp. ${start}-${end}`;
  }

  if (typeof start === "number") {
    return `p. ${start}`;
  }

  return "Page not available";
}


/**
 * We intentionally use semantic similarity for
 * groundedScore.
 *
 * rerank_score can exceed 1 because it contains
 * metadata bonuses, so it is NOT suitable for a
 * 0..1 confidence score.
 */
function getSemanticScore(
  chunk: BackendChunk
): number {

  const score =
    chunk.semantic_score ??
    chunk.similarity ??
    0;

  if (!Number.isFinite(score)) {
    return 0;
  }

  return Math.max(
    0,
    Math.min(1, score)
  );
}


/**
 * Get recommendation strength when present in
 * chunk metadata.
 */
function getRecommendationStrength(
  chunk: BackendChunk
): string {

  const metadata =
    chunk.metadata ?? {};

  return (
    metadata.recommendation_strength ??
    metadata.recommendationStrength ??
    "Not specified"
  );
}


/**
 * Convert one Python backend result into the exact
 * RetrievedChunk format already used by the UI.
 */
function mapBackendChunk(
  chunk: BackendChunk
): RetrievedChunk {

  const content =
    cleanClinicalText(
      chunk.text
    );

  const section =
    cleanClinicalText(
      chunk.section
    );

  const subsection =
    cleanClinicalText(
      chunk.subsection
    );

  const fullSection =
    subsection
      ? `${section} — ${subsection}`
      : section || "Section not available";

  return {
    id:
      chunk.chunk_id ??
      chunk.id ??
      crypto.randomUUID(),

    title:
      buildChunkTitle(chunk),

    source:
      buildSourceName(chunk),

    section:
      fullSection,

    page:
      buildPageLabel(chunk),

    similarityScore:
      getSemanticScore(chunk),

    recommendationStrength:
      getRecommendationStrength(
        chunk
      ),

    content,
  };
}


/**
 * Build citations strictly from retrieved metadata.
 *
 * Nothing is invented by the frontend.
 */
function buildCitations(
  chunks: RetrievedChunk[]
): MessageCitation[] {

  return chunks.map(
    (chunk) => {

      const cleanQuote =
        chunk.content.trim();

      const quote =
        cleanQuote.length > 180
          ? `${cleanQuote.slice(0, 180)}...`
          : cleanQuote;

      return {
        id:
          chunk.id,

        source:
          chunk.source,

        section:
          chunk.section,

        page:
          chunk.page,

        quote,

        relevanceScore:
          chunk.similarityScore,

        strength:
          (
            chunk.recommendationStrength ||
            "Not specified"
          ) as MessageCitation["strength"],
      };
    }
  );
}


/**
 * Build a conservative WHO vs NICE display.
 *
 * This is NOT an LLM-generated medical comparison.
 * It only exposes retrieved evidence from each
 * organization.
 */
function buildGuidelineComparison(
  backendChunks: BackendChunk[]
): RetrievedEvidence["guidelineComparison"] {

  const whoChunks =
    backendChunks.filter(
      (chunk) =>
        chunk.organization?.toUpperCase() ===
        "WHO"
    );

  const niceChunks =
    backendChunks.filter(
      (chunk) =>
        chunk.organization?.toUpperCase() ===
        "NICE"
    );


  if (
    whoChunks.length === 0 ||
    niceChunks.length === 0
  ) {
    return undefined;
  }


  const whoEvidence =
    cleanClinicalText(
      whoChunks[0]?.text
    );

  const niceEvidence =
    cleanClinicalText(
      niceChunks[0]?.text
    );


  const shorten = (
    text: string,
    maxLength: number = 350
  ) => {

    if (
      text.length <= maxLength
    ) {
      return text;
    }

    return (
      text.slice(
        0,
        maxLength
      ) + "..."
    );
  };


  return {
    whoStance:
      shorten(
        whoEvidence
      ),

    niceStance:
      shorten(
        niceEvidence
      ),

    consensus:
      "Relevant evidence was retrieved from both WHO and NICE. The final clinical comparison should be generated from these retrieved sources without merging the guidelines into a single recommendation.",
  };
}


/**
 * REAL CardioRAG evidence retrieval.
 *
 * Flow:
 *
 * Browser
 *   ↓
 * Next.js /api/retrieve
 *   ↓
 * FastAPI
 *   ↓
 * Query Classifier
 *   ↓
 * BGE-M3
 *   ↓
 * Supabase pgvector
 *   ↓
 * Metadata-aware reranker
 *   ↓
 * Real guideline chunks
 */
export async function retrieveClinicalEvidence(
  query: string,
  topK: number = 5
): Promise<RetrievedEvidence> {

  const trimmedQuery =
    query.trim();


  if (!trimmedQuery) {

    return {
      chunks: [],

      citations: [],

      groundedScore: 0,

      isInsufficientEvidence: true,

      guidelineComparison:
        undefined,

      retrievalMode:
        "empty_query",

      queryProfile: {},

      candidateCount: 0,
    };
  }


  // ============================================
  // CALL REAL NEXT.JS RETRIEVAL API
  // ============================================

  const response =
    await fetch(
      "/api/retrieve",
      {
        method: "POST",

        headers: {
          "Content-Type":
            "application/json",
        },

        body:
          JSON.stringify({
            query:
              trimmedQuery,
          }),

        cache:
          "no-store",
      }
    );


  if (!response.ok) {

    const errorText =
      await response.text();

    console.error(
      "CardioRAG retrieval error:",
      response.status,
      errorText
    );

    throw new Error(
      `Clinical evidence retrieval failed (${response.status})`
    );
  }


  const data:
    BackendResponse =
      await response.json();


  // ============================================
  // SELECT TOP RESULTS
  // ============================================

  const backendChunks =
    (
      data.results ?? []
    ).slice(
      0,
      topK
    );


  // ============================================
  // MAP PYTHON → EXISTING FRONTEND TYPE
  // ============================================

  const chunks:
    RetrievedChunk[] =
      backendChunks.map(
        mapBackendChunk
      );


  // ============================================
  // BUILD REAL CITATIONS
  // ============================================

  const citations =
    buildCitations(
      chunks
    );


  // ============================================
  // GROUNDED SCORE
  //
  // IMPORTANT:
  // Use semantic similarity, not rerank score.
  //
  // Rerank score can be >1.0.
  // ============================================

  const avgSimilarity =
    chunks.length > 0
      ? chunks.reduce(
          (
            total,
            chunk
          ) =>
            total +
            chunk.similarityScore,
          0
        ) / chunks.length
      : 0;


  const groundedScore =
    Math.round(
      avgSimilarity * 100
    ) / 100;


  // ============================================
  // INSUFFICIENT EVIDENCE
  // ============================================

  const bestScore =
    chunks.length > 0
      ? Math.max(
          ...chunks.map(
            (chunk) =>
              chunk.similarityScore
          )
        )
      : 0;


  const isInsufficientEvidence =
    chunks.length === 0 ||
    bestScore < 0.55;


  // ============================================
  // WHO vs NICE
  // ============================================

  const guidelineComparison =
    buildGuidelineComparison(
      backendChunks
    );


  // ============================================
  // RETURN IN SAME STRUCTURE AS OLD MOCK
  // ============================================

  return {
    chunks,

    citations,

    groundedScore,

    isInsufficientEvidence,

    guidelineComparison,

    retrievalMode:
      data.retrieval_mode,

    queryProfile:
      data.profile,

    candidateCount:
      data.candidate_count,
  };
}