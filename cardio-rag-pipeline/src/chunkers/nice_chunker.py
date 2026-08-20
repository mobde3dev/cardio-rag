"""
Semantic chunking engine for the NICE3 (NG238) cardiovascular guideline.

Splits section blocks into medically meaningful chunks:
  - Recommendations → individual self-contained chunks (one per ID)
  - Committee rationale → separate chunks linked to recommendations
  - Implementation impact → separate chunks (priority 3)
  - Lifestyle → separate chunks per subtopic
  - Definitions → one chunk per term
  - Research recommendations → separate (priority 3)
  - Update information → separate (priority 3)

Includes token counting and deterministic chunk ID generation.
"""

import re
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple, Set

from src.core.clean_text import clean_chunk_noise
from src.segmenters.nice_segmenter import (
    NiceSection,
    NiceSectionBlock,
    detect_subheadings,
    get_subtopic_for_subheading,
    is_committee_rationale,
    is_implementation_impact,
)
from src.segmenters.nice_rec_parser import (
    NiceRecommendation,
    extract_recommendations,
    find_date_markers,
    extract_cross_references,
    extract_technology_appraisals,
)
from src.enrichers.nice_enricher import (
    build_nice3_chunk_metadata,
    classify_content_type,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Token counter
# ---------------------------------------------------------------------------

class TokenCounter:
    """Configurable token counter for chunk sizing."""

    def __init__(self, encoding_name: str = "cl100k_base"):
        try:
            import tiktoken
            self.encoding = tiktoken.get_encoding(encoding_name)
            self._method = f"tiktoken_{encoding_name}"
        except Exception:
            self.encoding = None
            self._method = "word_estimate"
            logger.warning("tiktoken not available, using word-based estimate")

    @property
    def method(self) -> str:
        return self._method

    def count(self, text: str) -> int:
        if self.encoding:
            return len(self.encoding.encode(text))
        return int(len(text.split()) * 1.3)


_counter = TokenCounter()


def count_tokens(text: str) -> int:
    """Count tokens in text."""
    return _counter.count(text)


# ---------------------------------------------------------------------------
# Chunk data structure
# ---------------------------------------------------------------------------

@dataclass
class NiceChunk:
    """A single RAG chunk for NICE3."""
    chunk_id: str
    text: str
    token_count: int = 0
    metadata: Dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Chunk ID generation
# ---------------------------------------------------------------------------

_id_counters: Dict[str, int] = {}


def reset_id_counters():
    """Reset chunk ID counters (call at start of pipeline)."""
    global _id_counters
    _id_counters = {}


def _type_code(content_type: str) -> str:
    """Map content type to short code for chunk IDs."""
    mapping = {
        "recommendation": "REC",
        "committee_rationale": "RATIONALE",
        "implementation_impact": "IMPACT",
        "risk_assessment_guidance": "RISK",
        "lifestyle_guidance": "LIFE",
        "drug_guidance": "DRUG",
        "lipid_target": "LIPID",
        "laboratory_guidance": "LAB",
        "monitoring_guidance": "MON",
        "specialist_referral": "REF",
        "contraindication": "CONTRA",
        "adverse_effect_guidance": "AE",
        "pregnancy_guidance": "PREG",
        "definition": "TERM",
        "technology_appraisal_reference": "TA",
        "research_recommendation": "RESEARCH",
        "context": "CTX",
        "update_information": "UPDATE",
        "other": "OTH",
    }
    return mapping.get(content_type, "OTH")


def generate_chunk_id(
    section_number: str,
    content_type: str,
    recommendation_id: Optional[str] = None,
    subtopic_key: Optional[str] = None,
) -> str:
    """Generate a deterministic chunk ID.

    For recommendations: NICE3_1.7.1_REC
    For rationale: NICE3_1.7_RATIONALE_001
    For impact: NICE3_1.7_IMPACT_001
    For definitions: NICE3_TERM_{subtopic_key}_001
    """
    if recommendation_id and content_type == "recommendation":
        return f"NICE3_{recommendation_id}_REC"

    code = _type_code(content_type)
    if content_type == "definition" and subtopic_key:
        key_clean = re.sub(r"\W+", "_", subtopic_key.upper())[:30]
        base = f"NICE3_TERM_{key_clean}"
    else:
        sec = section_number if section_number else "0"
        if subtopic_key:
            key_clean = re.sub(r"\W+", "_", subtopic_key.upper())[:20]
            base = f"NICE3_{sec}_{code}_{key_clean}"
        else:
            base = f"NICE3_{sec}_{code}"

    _id_counters[base] = _id_counters.get(base, 0) + 1
    seq = _id_counters[base]

    return f"{base}_{seq:03d}"


# ---------------------------------------------------------------------------
# Text splitting utilities
# ---------------------------------------------------------------------------

def _split_into_paragraphs(text: str) -> List[str]:
    """Split text into paragraphs (on double newlines)."""
    paragraphs = re.split(r"\n\s*\n", text)
    return [p.strip() for p in paragraphs if p.strip()]


def _split_into_sentences(text: str) -> List[str]:
    """Split text into sentences, careful not to split on abbreviations."""
    protected = text
    for abbr in ["Dr.", "Mr.", "Mrs.", "Ms.", "e.g.", "i.e.", "vs.", "etc.",
                 "Fig.", "No.", "Vol.", "al.", "Jan.", "Feb.", "p."]:
        protected = protected.replace(abbr, abbr.replace(".", "@@DOT@@"))

    sentences = re.split(r"(?<=[.!?])\s+", protected)
    return [s.replace("@@DOT@@", ".").strip() for s in sentences if s.strip()]


# ---------------------------------------------------------------------------
# Chunk a single NICE recommendation
# ---------------------------------------------------------------------------

def chunk_recommendation(
    recommendation: NiceRecommendation,
    section: NiceSection,
    pdf_page_start: int,
    pdf_page_end: int,
    page_label_start: Optional[str] = None,
    page_label_end: Optional[str] = None,
    subsection: Optional[str] = None,
) -> NiceChunk:
    """Create a self-contained recommendation chunk.

    Includes section context + subsection + recommendation text + date marker.
    """
    # Build context prefix
    parts = []
    parts.append(f"Section: {section.full_heading}")
    if subsection:
        parts.append(f"Subheading: {subsection}")
    parts.append(f"Recommendation: {recommendation.recommendation_id}")
    parts.append("")
    parts.append(recommendation.text)

    full_text = "\n".join(parts)

    chunk_id = generate_chunk_id(
        section.number,
        "recommendation",
        recommendation_id=recommendation.recommendation_id,
    )

    metadata = build_nice3_chunk_metadata(
        text=full_text,
        section=section,
        pdf_page_start=pdf_page_start,
        pdf_page_end=pdf_page_end,
        page_label_start=page_label_start,
        page_label_end=page_label_end,
        content_type="recommendation",
        recommendation=recommendation,
        subsection=subsection,
    )

    tokens = count_tokens(full_text)
    metadata["token_count"] = tokens

    return NiceChunk(
        chunk_id=chunk_id,
        text=full_text,
        token_count=tokens,
        metadata=metadata,
    )


# ---------------------------------------------------------------------------
# Chunk committee rationale (may produce multiple chunks)
# ---------------------------------------------------------------------------

def chunk_rationale(
    text: str,
    section: NiceSection,
    pdf_page_start: int,
    pdf_page_end: int,
    page_label_start: Optional[str] = None,
    page_label_end: Optional[str] = None,
    related_recommendations: Optional[List[str]] = None,
    target_tokens: int = 600,
    max_tokens: int = 900,
    overlap_tokens: int = 75,
) -> List[NiceChunk]:
    """Split a committee rationale section into semantically bounded chunks.

    Prefers splitting at semantic boundaries (clinical evidence,
    economic evidence, cost effectiveness, implementation reasoning).
    """
    section_ctx = f"Section: {section.full_heading}\nWhy the committee made these recommendations\n\n"
    ctx_tokens = count_tokens(section_ctx)

    # Clean the text: remove the heading itself
    clean_text = re.sub(
        r"^\s*Why\s+the\s+committee\s+made\s+(?:the|these)?\s*recommendations?\s*\n*",
        "", text, flags=re.IGNORECASE
    ).strip()

    full_single = section_ctx + clean_text
    if count_tokens(full_single) <= max_tokens:
        chunk_id = generate_chunk_id(section.number, "committee_rationale")
        metadata = build_nice3_chunk_metadata(
            text=full_single,
            section=section,
            pdf_page_start=pdf_page_start,
            pdf_page_end=pdf_page_end,
            page_label_start=page_label_start,
            page_label_end=page_label_end,
            content_type="committee_rationale",
            related_recommendations=related_recommendations,
        )
        tokens = count_tokens(full_single)
        metadata["token_count"] = tokens
        return [NiceChunk(chunk_id=chunk_id, text=full_single, token_count=tokens, metadata=metadata)]

    # Split at sentence boundaries with overlap
    sentences = _split_into_sentences(clean_text)
    if not sentences:
        sentences = [clean_text]

    chunks: List[NiceChunk] = []
    current_sentences: List[str] = []
    current_tokens = 0

    for sent in sentences:
        st = count_tokens(sent)
        if current_sentences and (ctx_tokens + current_tokens + st > target_tokens):
            chunk_text = section_ctx + " ".join(current_sentences)
            chunk_id = generate_chunk_id(section.number, "committee_rationale")
            metadata = build_nice3_chunk_metadata(
                text=chunk_text,
                section=section,
                pdf_page_start=pdf_page_start,
                pdf_page_end=pdf_page_end,
                page_label_start=page_label_start,
                page_label_end=page_label_end,
                content_type="committee_rationale",
                related_recommendations=related_recommendations,
            )
            tokens = count_tokens(chunk_text)
            metadata["token_count"] = tokens
            chunks.append(NiceChunk(chunk_id=chunk_id, text=chunk_text, token_count=tokens, metadata=metadata))

            # Overlap
            overlap_sents = []
            ot = 0
            for s in reversed(current_sentences):
                if ot + count_tokens(s) > overlap_tokens:
                    break
                overlap_sents.insert(0, s)
                ot += count_tokens(s)
            current_sentences = list(overlap_sents) + [sent]
            current_tokens = sum(count_tokens(s) for s in current_sentences)
        else:
            current_sentences.append(sent)
            current_tokens += st

    if current_sentences:
        chunk_text = section_ctx + " ".join(current_sentences)
        chunk_id = generate_chunk_id(section.number, "committee_rationale")
        metadata = build_nice3_chunk_metadata(
            text=chunk_text,
            section=section,
            pdf_page_start=pdf_page_start,
            pdf_page_end=pdf_page_end,
            page_label_start=page_label_start,
            page_label_end=page_label_end,
            content_type="committee_rationale",
            related_recommendations=related_recommendations,
        )
        tokens = count_tokens(chunk_text)
        metadata["token_count"] = tokens
        chunks.append(NiceChunk(chunk_id=chunk_id, text=chunk_text, token_count=tokens, metadata=metadata))

    return chunks


# ---------------------------------------------------------------------------
# Chunk implementation impact
# ---------------------------------------------------------------------------

def chunk_implementation_impact(
    text: str,
    section: NiceSection,
    pdf_page_start: int,
    pdf_page_end: int,
    page_label_start: Optional[str] = None,
    page_label_end: Optional[str] = None,
    related_recommendations: Optional[List[str]] = None,
) -> NiceChunk:
    """Create an implementation impact chunk (priority 3)."""
    section_ctx = f"Section: {section.full_heading}\nHow the recommendations might affect practice\n\n"
    clean_text = re.sub(
        r"^\s*How\s+the\s+recommendations?\s+might\s+affect\s+(?:practice|services|the\s+NHS)\s*\n*",
        "", text, flags=re.IGNORECASE
    ).strip()
    full_text = section_ctx + clean_text

    chunk_id = generate_chunk_id(section.number, "implementation_impact")
    metadata = build_nice3_chunk_metadata(
        text=full_text,
        section=section,
        pdf_page_start=pdf_page_start,
        pdf_page_end=pdf_page_end,
        page_label_start=page_label_start,
        page_label_end=page_label_end,
        content_type="implementation_impact",
        related_recommendations=related_recommendations,
    )
    tokens = count_tokens(full_text)
    metadata["token_count"] = tokens

    return NiceChunk(chunk_id=chunk_id, text=full_text, token_count=tokens, metadata=metadata)


# ---------------------------------------------------------------------------
# Chunk definitions
# ---------------------------------------------------------------------------

def chunk_definitions(
    text: str,
    section: NiceSection,
    pdf_page_start: int,
    pdf_page_end: int,
    page_label_start: Optional[str] = None,
    page_label_end: Optional[str] = None,
) -> List[NiceChunk]:
    """Split glossary terms into individual definition chunks.

    Each distinct definition becomes a separate chunk.
    """
    chunks: List[NiceChunk] = []

    # Remove section heading
    clean = re.sub(r"^\s*Terms?\s+used\s+in\s+this\s+guideline\s*\n*", "", text, flags=re.IGNORECASE).strip()

    # Try to split on definition-like patterns (bolded term + description)
    # Common patterns: term on its own line, followed by definition paragraph
    paragraphs = _split_into_paragraphs(clean)

    i = 0
    while i < len(paragraphs):
        para = paragraphs[i]
        # Check if this looks like a term heading (short, possibly bold)
        if len(para.split()) <= 10 and i + 1 < len(paragraphs):
            term_name = para.strip()
            definition = paragraphs[i + 1].strip()
            full_text = f"Definition: {term_name}\n\n{definition}"
            i += 2
        else:
            term_name = para[:50].strip()
            full_text = f"Definition:\n\n{para}"
            i += 1

        chunk_id = generate_chunk_id(section.number, "definition", subtopic_key=term_name)
        metadata = build_nice3_chunk_metadata(
            text=full_text,
            section=section,
            pdf_page_start=pdf_page_start,
            pdf_page_end=pdf_page_end,
            page_label_start=page_label_start,
            page_label_end=page_label_end,
            content_type="definition",
        )
        tokens = count_tokens(full_text)
        metadata["token_count"] = tokens

        chunks.append(NiceChunk(
            chunk_id=chunk_id,
            text=full_text,
            token_count=tokens,
            metadata=metadata,
        ))

    return chunks


# ---------------------------------------------------------------------------
# Chunk generic narrative (for non-recommendation sections)
# ---------------------------------------------------------------------------

def chunk_narrative(
    text: str,
    section: NiceSection,
    content_type: str,
    pdf_page_start: int,
    pdf_page_end: int,
    page_label_start: Optional[str] = None,
    page_label_end: Optional[str] = None,
    subsection: Optional[str] = None,
    target_tokens: int = 600,
    max_tokens: int = 900,
    overlap_tokens: int = 75,
) -> List[NiceChunk]:
    """Chunk a generic narrative block with token-bounded splitting."""
    section_ctx = f"Section: {section.full_heading}\n"
    if subsection:
        section_ctx += f"Subheading: {subsection}\n"
    section_ctx += "\n"
    ctx_tokens = count_tokens(section_ctx)

    full_single = section_ctx + text
    if count_tokens(full_single) <= max_tokens:
        chunk_id = generate_chunk_id(section.number, content_type, subtopic_key=subsection)
        metadata = build_nice3_chunk_metadata(
            text=full_single,
            section=section,
            pdf_page_start=pdf_page_start,
            pdf_page_end=pdf_page_end,
            page_label_start=page_label_start,
            page_label_end=page_label_end,
            content_type=content_type,
            subsection=subsection,
        )
        tokens = count_tokens(full_single)
        metadata["token_count"] = tokens
        return [NiceChunk(chunk_id=chunk_id, text=full_single, token_count=tokens, metadata=metadata)]

    sentences = _split_into_sentences(text)
    if not sentences:
        sentences = [text]

    chunks: List[NiceChunk] = []
    current_sentences: List[str] = []
    current_tokens = 0

    for sent in sentences:
        st = count_tokens(sent)
        if current_sentences and (ctx_tokens + current_tokens + st > target_tokens):
            chunk_text = section_ctx + " ".join(current_sentences)
            chunk_id = generate_chunk_id(section.number, content_type, subtopic_key=subsection)
            metadata = build_nice3_chunk_metadata(
                text=chunk_text,
                section=section,
                pdf_page_start=pdf_page_start,
                pdf_page_end=pdf_page_end,
                page_label_start=page_label_start,
                page_label_end=page_label_end,
                content_type=content_type,
                subsection=subsection,
            )
            tokens = count_tokens(chunk_text)
            metadata["token_count"] = tokens
            chunks.append(NiceChunk(chunk_id=chunk_id, text=chunk_text, token_count=tokens, metadata=metadata))

            overlap_sents = []
            ot = 0
            for s in reversed(current_sentences):
                if ot + count_tokens(s) > overlap_tokens:
                    break
                overlap_sents.insert(0, s)
                ot += count_tokens(s)
            current_sentences = list(overlap_sents) + [sent]
            current_tokens = sum(count_tokens(s) for s in current_sentences)
        else:
            current_sentences.append(sent)
            current_tokens += st

    if current_sentences:
        chunk_text = section_ctx + " ".join(current_sentences)
        chunk_id = generate_chunk_id(section.number, content_type, subtopic_key=subsection)
        metadata = build_nice3_chunk_metadata(
            text=chunk_text,
            section=section,
            pdf_page_start=pdf_page_start,
            pdf_page_end=pdf_page_end,
            page_label_start=page_label_start,
            page_label_end=page_label_end,
            content_type=content_type,
            subsection=subsection,
        )
        tokens = count_tokens(chunk_text)
        metadata["token_count"] = tokens
        chunks.append(NiceChunk(chunk_id=chunk_id, text=chunk_text, token_count=tokens, metadata=metadata))

    return chunks


# ---------------------------------------------------------------------------
# Process a full section block
# ---------------------------------------------------------------------------

def chunk_nice_section_block(
    section_block: NiceSectionBlock,
) -> List[NiceChunk]:
    """Process a NiceSectionBlock into a list of NiceChunks.

    Strategy:
    1. Extract individual recommendations → one chunk each
    2. Detect committee rationale → separate chunks
    3. Detect implementation impact → separate chunks
    4. For definitions section → one chunk per term
    5. Remaining narrative → token-bounded chunks with semantic splitting
    """
    section = section_block.section
    text = section_block.text
    sec_num = section.number

    if not text.strip():
        return []

    chunks: List[NiceChunk] = []
    p_start = section_block.pdf_page_start
    p_end = section_block.pdf_page_end
    l_start = section_block.page_label_start
    l_end = section_block.page_label_end

    # Skip the top-level "Recommendations" heading block
    if sec_num == "recommendations":
        return []

    # ------------------------------------------------------------------
    # Definitions section
    # ------------------------------------------------------------------
    if sec_num == "terms":
        return chunk_definitions(text, section, p_start, p_end, l_start, l_end)

    # ------------------------------------------------------------------
    # Detect subheadings for context
    # ------------------------------------------------------------------
    subheadings = detect_subheadings(text)

    # ------------------------------------------------------------------
    # Split text into sub-blocks by subheading boundaries
    # ------------------------------------------------------------------
    sub_blocks: List[Tuple[Optional[str], str]] = []  # (subheading, text)

    if subheadings:
        # Add text before first subheading
        if subheadings[0][0] > 0:
            pre_text = text[:subheadings[0][0]].strip()
            if pre_text:
                sub_blocks.append((None, pre_text))

        for i, (pos, sub_title) in enumerate(subheadings):
            end_pos = subheadings[i + 1][0] if i + 1 < len(subheadings) else len(text)
            sub_text = text[pos:end_pos].strip()
            if sub_text:
                sub_blocks.append((sub_title, sub_text))
    else:
        sub_blocks.append((None, text))

    # ------------------------------------------------------------------
    # Process each sub-block
    # ------------------------------------------------------------------
    for sub_heading, sub_text in sub_blocks:
        # Check for committee rationale
        if is_committee_rationale(sub_text):
            # Collect recommendation IDs from previously created rec chunks
            related_recs = [c.metadata.get("recommendation_id")
                          for c in chunks
                          if c.metadata.get("recommendation_id")]
            rationale_chunks = chunk_rationale(
                sub_text, section, p_start, p_end, l_start, l_end,
                related_recommendations=related_recs if related_recs else None,
            )
            chunks.extend(rationale_chunks)
            continue

        # Check for implementation impact
        if is_implementation_impact(sub_text):
            related_recs = [c.metadata.get("recommendation_id")
                          for c in chunks
                          if c.metadata.get("recommendation_id")]
            impact_chunk = chunk_implementation_impact(
                sub_text, section, p_start, p_end, l_start, l_end,
                related_recommendations=related_recs if related_recs else None,
            )
            chunks.append(impact_chunk)
            continue

        # Extract recommendations from this sub-block
        recommendations = extract_recommendations(sub_text, sec_num)

        if recommendations:
            for rec in recommendations:
                rec_chunk = chunk_recommendation(
                    rec, section, p_start, p_end, l_start, l_end,
                    subsection=sub_heading,
                )
                chunks.append(rec_chunk)

            # Check for remaining non-recommendation text
            # (text before first recommendation, or between recommendations)
            if recommendations[0].start_offset > 0:
                pre_text = sub_text[:recommendations[0].start_offset].strip()
                # Remove section heading from pre_text
                pre_text = re.sub(
                    r"^\s*\d+\.\d+\s+[^\n]+\n*", "", pre_text
                ).strip()
                if pre_text and count_tokens(pre_text) > 20:
                    content_type = classify_content_type(pre_text, section)
                    narrative_chunks = chunk_narrative(
                        pre_text, section, content_type, p_start, p_end,
                        l_start, l_end, subsection=sub_heading,
                    )
                    chunks.extend(narrative_chunks)
        else:
            # No recommendations — chunk as narrative
            # Determine content type based on text and section
            content_type = classify_content_type(sub_text, section)

            # For research section
            if sec_num == "research":
                content_type = "research_recommendation"
            elif sec_num == "context":
                content_type = "context"
            elif sec_num == "update_info":
                content_type = "update_information"

            narrative_chunks = chunk_narrative(
                sub_text, section, content_type, p_start, p_end,
                l_start, l_end, subsection=sub_heading,
            )
            chunks.extend(narrative_chunks)

    for c in chunks:
        c.text = clean_chunk_noise(c.text)
        c.token_count = count_tokens(c.text)
        c.metadata["token_count"] = c.token_count

    return chunks
